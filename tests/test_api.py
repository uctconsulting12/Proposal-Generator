"""End-to-end API tests using a fake LLM and the vector stack disabled."""

from __future__ import annotations


def _intake(**overrides) -> dict:
    payload = {
        "client_name": "Acme",
        "job_title": "Build a REST API",
        "job_description": "Need a Python REST API with auth and tests.",
        "tech_stack": "Python, FastAPI",
    }
    payload.update(overrides)
    return payload


def _start(client) -> str:
    return client.post("/api/session/start", json=_intake()).json()["session_id"]


def _send(client, session_id: str, message: str) -> dict:
    return client.post(
        f"/api/session/{session_id}/message", json={"message": message}
    ).json()


# --- health --------------------------------------------------------------
def test_health_reports_status(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["rag_available"] is False
    assert body["ollama_reachable"] is True
    assert "X-Request-ID" in resp.headers


# --- session start -------------------------------------------------------
def test_start_session_begins_in_questioning_stage(client, fake_llm):
    resp = client.post("/api/session/start", json=_intake())
    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant"] == fake_llm.reply
    assert body["stage"] == "questioning"
    assert len(body["session_id"]) == 36


def test_start_session_skips_questions_when_disabled(make_client):
    no_q = make_client(enable_questions=False)
    body = no_q.post("/api/session/start", json=_intake()).json()
    assert body["stage"] == "draft"


def test_start_session_validates_required_fields(client):
    resp = client.post("/api/session/start", json={"client_name": "Acme"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"].startswith("Request validation failed")
    # The message names the offending fields.
    assert "job_title" in body["error"]
    assert "job_description" in body["error"]


def test_start_session_rejects_blank_job_title(client):
    resp = client.post("/api/session/start", json=_intake(job_title="   "))
    assert resp.status_code == 400


# --- workflow stages -----------------------------------------------------
def test_questioning_advances_to_draft_after_max_questions(client):
    session_id = _start(client)
    # max_questions=2: first answer stays in questioning, second reaches draft.
    assert _send(client, session_id, "answer one")["stage"] == "questioning"
    assert _send(client, session_id, "answer two")["stage"] == "draft"


def test_skip_command_jumps_straight_to_draft(client):
    session_id = _start(client)
    assert _send(client, session_id, "/draft")["stage"] == "draft"


def test_draft_approval_reaches_final(client):
    session_id = _start(client)
    _send(client, session_id, "/draft")  # -> draft
    assert _send(client, session_id, "approve")["stage"] == "final"


def test_draft_feedback_stays_in_draft(client):
    session_id = _start(client)
    _send(client, session_id, "/draft")  # -> draft
    result = _send(client, session_id, "make the timeline shorter")
    assert result["stage"] == "draft"


def test_final_stage_allows_free_chat(client):
    session_id = _start(client)
    _send(client, session_id, "/draft")
    _send(client, session_id, "approve")  # -> final
    assert _send(client, session_id, "tweak the intro")["stage"] == "final"


# --- finalize ------------------------------------------------------------
def test_finalize_locks_the_session(client):
    session_id = _start(client)
    resp = client.post(f"/api/session/{session_id}/finalize")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "closed": True}


def test_finalized_session_allows_qa_messages(client):
    session_id = _start(client)
    client.post(f"/api/session/{session_id}/finalize")
    resp = client.post(
        f"/api/session/{session_id}/message", json={"message": "hello"}
    )
    assert resp.status_code == 200
    assert resp.json()["stage"] == "final"


def test_finalize_unknown_session_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(f"/api/session/{fake_id}/finalize")
    assert resp.status_code == 404


# --- errors / validation -------------------------------------------------
def test_message_unknown_session_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.post(f"/api/session/{fake_id}/message", json={"message": "hi"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "Session not found"


def test_message_rejects_malformed_session_id(client):
    resp = client.post("/api/session/not-a-uuid/message", json={"message": "hi"})
    assert resp.status_code == 400


def test_message_rejects_blank_body(client):
    session_id = _start(client)
    resp = client.post(
        f"/api/session/{session_id}/message", json={"message": "   "}
    )
    assert resp.status_code == 400


def test_reindex_returns_503_when_vector_stack_disabled(client):
    resp = client.post("/api/kb/reindex")
    assert resp.status_code == 503
    assert "error" in resp.json()


def test_kb_upload_saves_file_and_returns_description(client):
    files = {"file": ("past_proposal.txt", b"Built a FastAPI service with JWT auth.", "text/plain")}
    resp = client.post("/api/kb/upload", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["filename"] == "past_proposal.txt"
    assert "client_uploads" in body["relative_path"]
    assert body["description"]


# --- conversation continuity --------------------------------------------
def test_session_carries_history_into_next_turn(client, fake_llm):
    session_id = _start(client)
    _send(client, session_id, "my answer here")
    last_call = fake_llm.calls[-1]
    assert any("my answer here" in m["content"] for m in last_call)
    assert last_call[0]["role"] == "system"


def test_session_list_returns_user_sessions(client):
    session_id = _start(client)
    resp = client.get("/api/session/list")
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert any(s["session_id"] == session_id for s in sessions)


def test_get_session_returns_display_messages(client):
    session_id = _start(client)
    _send(client, session_id, "my answer here")
    resp = client.get(f"/api/session/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert any(m["role"] == "assistant" for m in body["messages"])
