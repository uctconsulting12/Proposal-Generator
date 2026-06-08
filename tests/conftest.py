"""Shared pytest fixtures.

The vector stack is disabled for API tests (it would otherwise download an
embedding model), and the Ollama client is replaced with a deterministic fake.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.auth import require_user
from app.services import get_llm


class FakeLLM:
    """Deterministic stand-in for any LlmClient. Records every call."""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []
        self.reply = "Assistant response."

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.reply

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:  # pragma: no cover - trivial
        pass


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def make_client(tmp_path, fake_llm, monkeypatch):
    """Factory building isolated TestClients with optional settings overrides."""
    # Disable the optional vector stack so startup does not load a model.
    monkeypatch.setattr("app.rag._VECTOR_STACK_AVAILABLE", False)
    clients: list[TestClient] = []

    def _make(**overrides) -> TestClient:
        inst = tmp_path / f"inst{len(clients)}"
        inst.mkdir()
        # Pin workflow settings so tests stay deterministic regardless of the
        # developer's local .env; individual tests override as needed.
        base = {
            "max_sessions": 3,
            "max_messages_per_session": 8,
            "enable_questions": True,
            "max_questions": 2,
        }
        base.update(overrides)
        settings = Settings(
            sessions_file=inst / "web_sessions.json",
            kb_dir=inst / "knowledge_base",
            qdrant_path=inst / "qdrant_data",
            frontend_dir=inst / "frontend",
            **base,
        )
        app = create_app(settings)
        app.dependency_overrides[get_llm] = lambda: fake_llm
        app.dependency_overrides[require_user] = lambda: {
            "user_id": "test-user",
            "email": "test@example.com",
        }
        test_client = TestClient(app)
        test_client.__enter__()
        clients.append(test_client)
        return test_client

    yield _make

    for test_client in clients:
        test_client.__exit__(None, None, None)


@pytest.fixture
def client(make_client) -> TestClient:
    """A default TestClient (questions enabled, max_questions=2)."""
    return make_client()
