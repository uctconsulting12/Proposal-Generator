"""Thread-safe, atomic JSON-backed session store.

Persistence intentionally stays on a flat JSON file (no external database).
Production-safety is achieved by:
  * guarding all access with a re-entrant lock,
  * writing via a temp file + atomic ``os.replace`` so a crash mid-write can
    never corrupt the live file,
  * bounding memory with an LRU cap on sessions and a cap on message history.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, data: Any) -> None:
    """Write ``data`` as JSON to ``path`` via a temp file + atomic replace.

    A crash mid-write can never leave the destination file truncated.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


class SessionStore:
    """In-memory session map with durable, atomic JSON persistence."""

    def __init__(self, path: Path, *, max_sessions: int, max_messages: int) -> None:
        self._path = path
        self._max_sessions = max_sessions
        self._max_messages = max_messages
        self._lock = threading.RLock()
        self._sessions: dict[str, dict[str, Any]] = {}

    # -- lifecycle --------------------------------------------------------
    def load(self) -> None:
        """Load sessions from disk; tolerate a missing or corrupt file."""
        with self._lock:
            if not self._path.exists():
                self._sessions = {}
                return
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._sessions = data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load sessions file (%s); starting empty", exc)
                self._sessions = {}
            logger.info("Loaded %d session(s) from %s", len(self._sessions), self._path)

    def _persist(self) -> None:
        """Atomically write the current state to disk. Caller holds the lock."""
        atomic_write_json(self._path, self._sessions)

    # -- queries ----------------------------------------------------------
    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            session = self._sessions.get(session_id)
            return json.loads(json.dumps(session)) if session is not None else None

    # -- mutations --------------------------------------------------------
    def create(
        self,
        *,
        user_id: str,
        intake: dict[str, Any],
        messages: list[dict[str, str]],
        retrieved_chunks: list[dict[str, str]],
        stage: str,
    ) -> str:
        """Create a new session, evicting the oldest if at capacity."""
        session_id = str(uuid.uuid4())
        now = _utc_now()
        with self._lock:
            while len(self._sessions) >= self._max_sessions:
                oldest = next(iter(self._sessions))
                del self._sessions[oldest]
                logger.info("Evicted oldest session %s (capacity reached)", oldest)
            self._sessions[session_id] = {
                "user_id": user_id,
                "intake": intake,
                "messages": messages[-self._max_messages :],
                "retrieved_chunks": retrieved_chunks,
                "stage": stage,
                "questions_asked": 0,
                "closed": False,
                "created_at": now,
                "updated_at": now,
            }
            self._persist()
        return session_id

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        *,
        stage: str | None = None,
        questions_asked: int | None = None,
    ) -> None:
        """Append a user/assistant exchange and optionally update stage state."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            session["messages"].append({"role": "user", "content": user_message})
            session["messages"].append(
                {"role": "assistant", "content": assistant_message}
            )
            # Keep the system prompt (index 0) and cap the rolling history.
            messages = session["messages"]
            if len(messages) > self._max_messages:
                system = messages[:1]
                session["messages"] = system + messages[-(self._max_messages - 1) :]
            if stage is not None:
                session["stage"] = stage
            if questions_asked is not None:
                session["questions_asked"] = questions_asked
            session["updated_at"] = _utc_now()
            self._persist()

    def messages_for(self, session_id: str) -> list[dict[str, str]]:
        """Return a copy of the message history for an LLM call."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            return list(session["messages"])

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return lightweight session metadata for a user, newest first."""
        with self._lock:
            rows: list[dict[str, Any]] = []
            for session_id, session in self._sessions.items():
                if session.get("user_id") != user_id:
                    continue
                intake = session.get("intake", {})
                rows.append(
                    {
                        "session_id": session_id,
                        "job_title": str(intake.get("job_title", "")).strip() or "Untitled JD",
                        "stage": str(session.get("stage", "")),
                        "closed": bool(session.get("closed", False)),
                        "created_at": str(session.get("created_at", "")),
                        "updated_at": str(session.get("updated_at", "")),
                    }
                )
            rows.sort(key=lambda r: r["updated_at"], reverse=True)
            return rows

    def finalize(self, session_id: str) -> None:
        """Mark a session as finalized (closed to any further messages)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            session["closed"] = True
            session["updated_at"] = _utc_now()
            self._persist()

    def set_field(self, session_id: str, key: str, value: Any) -> None:
        """Persist an arbitrary session-level field (e.g. the cached PDF title).

        Used for derived state we want to compute once and reuse across
        requests — the LLM-generated PDF cover title is the first caller.
        ``updated_at`` is bumped so the dashboard reflects the change.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            session[key] = value
            session["updated_at"] = _utc_now()
            self._persist()

    def delete(self, session_id: str) -> None:
        """Remove a session entirely.

        Used by the Save/Discard prompt on finalize: the user can discard a
        session they don't want saved to history. Idempotent — deleting an
        unknown id is a silent no-op so a duplicate UI click can't 500.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._persist()

    def reopen(self, session_id: str) -> None:
        """Reopen a finalized session so messaging is allowed again.

        Stage is kept at its current value (almost always ``STAGE_FINAL``);
        the only state change is ``closed -> False``. Chat history and
        intake stay intact so the user can continue iterating on the
        existing proposal instead of starting over.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            session["closed"] = False
            session["updated_at"] = _utc_now()
            self._persist()
