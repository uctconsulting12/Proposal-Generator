"""Tests for the atomic JSON session store."""

from __future__ import annotations

import json

import pytest

from app.storage import SessionStore


def _store(tmp_path, max_sessions=10, max_messages=20) -> SessionStore:
    store = SessionStore(
        tmp_path / "sessions.json",
        max_sessions=max_sessions,
        max_messages=max_messages,
    )
    store.load()
    return store


def _new(store: SessionStore) -> str:
    return store.create(
        user_id="test-user",
        intake={"job_title": "Build API"},
        messages=[{"role": "system", "content": "sys"}],
        retrieved_chunks=[],
        stage="questioning",
    )


def test_create_and_get_roundtrip(tmp_path):
    store = _store(tmp_path)
    session_id = _new(store)
    session = store.get(session_id)
    assert session is not None
    assert session["intake"]["job_title"] == "Build API"
    assert session["created_at"] and session["updated_at"]


def test_get_returns_a_copy(tmp_path):
    store = _store(tmp_path)
    session_id = _new(store)
    store.get(session_id)["intake"]["job_title"] = "mutated"
    assert store.get(session_id)["intake"]["job_title"] == "Build API"


def test_persistence_survives_reload(tmp_path):
    store = _store(tmp_path)
    session_id = _new(store)
    reloaded = _store(tmp_path)
    assert reloaded.get(session_id) is not None


def test_append_turn_extends_history(tmp_path):
    store = _store(tmp_path)
    session_id = _new(store)
    store.append_turn(session_id, "hello", "hi there")
    messages = store.messages_for(session_id)
    assert messages[-2:] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_append_turn_unknown_session_raises(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(KeyError):
        store.append_turn("missing", "a", "b")


def test_message_history_is_capped_but_keeps_system_prompt(tmp_path):
    store = _store(tmp_path, max_messages=5)
    session_id = _new(store)
    for i in range(10):
        store.append_turn(session_id, f"u{i}", f"a{i}")
    messages = store.messages_for(session_id)
    assert len(messages) <= 5
    assert messages[0] == {"role": "system", "content": "sys"}


def test_lru_eviction_at_capacity(tmp_path):
    store = _store(tmp_path, max_sessions=2)
    first = _new(store)
    _new(store)
    _new(store)
    assert store.count() == 2
    assert store.get(first) is None


def test_corrupt_file_loads_as_empty(tmp_path):
    path = tmp_path / "sessions.json"
    path.write_text("{not json", encoding="utf-8")
    store = SessionStore(path, max_sessions=10, max_messages=20)
    store.load()
    assert store.count() == 0


def test_stage_is_stored_and_updatable(tmp_path):
    store = _store(tmp_path)
    session_id = _new(store)
    assert store.get(session_id)["stage"] == "questioning"
    assert store.get(session_id)["questions_asked"] == 0

    store.append_turn(session_id, "u", "a", stage="draft", questions_asked=2)
    session = store.get(session_id)
    assert session["stage"] == "draft"
    assert session["questions_asked"] == 2


def test_persisted_file_is_valid_json(tmp_path):
    store = _store(tmp_path)
    _new(store)
    data = json.loads((tmp_path / "sessions.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict) and len(data) == 1
