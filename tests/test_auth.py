"""Tests for JWT auth helpers and auth endpoints."""

from __future__ import annotations

from bson import ObjectId
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import Settings
from app.main import create_app
from app.services import get_llm


class FakeLLM:
    async def chat(self, messages: list[dict[str, str]]) -> str:
        return "ok"

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


def test_auth_me_rejects_missing_token(tmp_path, monkeypatch):
    monkeypatch.setattr("app.rag._VECTOR_STACK_AVAILABLE", False)
    settings = Settings(
        sessions_file=tmp_path / "web_sessions.json",
        kb_dir=tmp_path / "knowledge_base",
        qdrant_path=tmp_path / "qdrant_data",
        frontend_dir=tmp_path / "frontend",
        jwt_secret="secret",
    )
    app = create_app(settings)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    with TestClient(app) as client:
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


def test_auth_me_accepts_valid_token(tmp_path, monkeypatch):
    monkeypatch.setattr("app.rag._VECTOR_STACK_AVAILABLE", False)
    settings = Settings(
        sessions_file=tmp_path / "web_sessions.json",
        kb_dir=tmp_path / "knowledge_base",
        qdrant_path=tmp_path / "qdrant_data",
        frontend_dir=tmp_path / "frontend",
        jwt_secret="secret",
    )
    app = create_app(settings)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    token = create_access_token(settings, user_id="u1", email="a@b.com")
    with TestClient(app) as client:
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "a@b.com"


def test_signup_returns_token(monkeypatch, client):
    def _fake_create_user(settings, email, password):
        return {"_id": ObjectId(), "email": email}

    monkeypatch.setattr("app.routers.auth.create_user", _fake_create_user)
    resp = client.post(
        "/api/auth/signup",
        json={"email": "new@user.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_signin_returns_token(monkeypatch, client):
    def _fake_authenticate_user(settings, email, password):
        return {"_id": ObjectId(), "email": email}

    monkeypatch.setattr("app.routers.auth.authenticate_user", _fake_authenticate_user)
    resp = client.post(
        "/api/auth/signin",
        json={"email": "existing@user.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
