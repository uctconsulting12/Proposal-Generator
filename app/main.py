"""FastAPI application factory.

Wires together configuration, logging, services, middleware, routers, error
handling and static-file serving for the JD Proposal Copilot.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .auth import require_user
from .config import Settings, get_settings
from .errors import register_exception_handlers
from .llm import create_llm_client
from .logging_config import configure_logging, request_id_var
from .rag import RagService
from .routers import auth, health, kb, profile, sessions, templates
from .services import Services
from .storage import SessionStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build services on startup and release them on shutdown."""
    settings: Settings = app.state.settings

    store = SessionStore(
        settings.sessions_file,
        max_sessions=settings.max_sessions,
        max_messages=settings.max_messages_per_session,
    )
    store.load()

    llm = create_llm_client(settings)
    rag = RagService(settings)

    # Build the vector index up front so the first request is fast. A failure
    # here is non-fatal: the app still serves, retrieval just degrades.
    if rag.available:
        try:
            await run_in_threadpool(rag.reindex)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Initial KB index build failed: %s", exc)
    else:
        logger.warning("Vector dependencies missing; RAG retrieval disabled")

    app.state.services = Services(settings=settings, store=store, llm=llm, rag=rag)
    logger.info("Application startup complete (v%s)", __version__)

    try:
        yield
    finally:
        await llm.aclose()
        await run_in_threadpool(rag.close)
        logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title="JD Proposal Copilot",
        version=__version__,
        description="Upwork proposal copilot with RAG over past project documents.",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def _request_context(request: Request, call_next) -> Response:
        """Tag each request with an id and log its outcome and latency."""
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_var.set(req_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = req_id
        logger.info(
            "%s %s -> %s (%.0f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    register_exception_handlers(app)

    # /health stays public so load balancers / monitors can probe without a key.
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(profile.router)
    app.include_router(templates.router)
    app.include_router(kb.router, dependencies=[Depends(require_user)])

    # Optionally serve the built React bundle from the same process. The React
    # frontend now runs on its own dev server (port 5173) during development,
    # so this is opt-in via ``COPILOT_SERVE_FRONTEND=true`` for single-port
    # production deployments.
    if settings.serve_frontend and settings.frontend_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=settings.frontend_dir, html=True),
            name="frontend",
        )
    return app


app = create_app()
