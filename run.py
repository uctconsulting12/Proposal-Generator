"""Development/production entrypoint.

Usage:
    python run.py                 # use settings (env / .env)
    python run.py --reload        # auto-reload for local development
    python run.py --host 0.0.0.0 --port 9000

In production prefer running uvicorn directly:
    uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1

Note: keep ``--workers 1``. The local Qdrant store and the JSON session file
are single-process resources; multiple workers would race on them.
"""

from __future__ import annotations

import argparse
import logging
import socket

import uvicorn

from app.config import get_settings

logger = logging.getLogger("run")


def _port_is_free(host: str, port: int) -> bool:
    """Return True if ``host:port`` can be bound right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _resolve_port(host: str, start: int, span: int = 20) -> int:
    """Find the first bindable port at or after ``start``.

    Windows reserves ranges of ports (Hyper-V, WinNAT), so the configured port
    may fail with WinError 10013 even when nothing is listening. Scanning a
    small range keeps the app launchable without manual reconfiguration.
    """
    for port in range(start, start + span):
        if _port_is_free(host, port):
            if port != start:
                logger.warning("Port %d unavailable; using %d instead", start, port)
            return port
    raise SystemExit(
        f"No free port found in range {start}-{start + span - 1} on {host}."
    )


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="JD Proposal Copilot server")
    parser.add_argument("--host", default=settings.host)
    parser.add_argument("--port", type=int, default=settings.port)
    parser.add_argument("--reload", action="store_true", help="enable auto-reload")
    args = parser.parse_args()

    port = _resolve_port(args.host, args.port)
    print(f"Starting JD Proposal Copilot at http://{args.host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=port,
        reload=args.reload,
        log_config=None,  # logging is configured by the application itself
    )


if __name__ == "__main__":
    main()
