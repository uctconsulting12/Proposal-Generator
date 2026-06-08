"""Tests for proposal PDF rendering and the export endpoint."""

from __future__ import annotations

from app.pdf import parse_proposal, render_proposal_pdf

_SAMPLE = """\
Introduction
We are excited to help with this project.

Proposed Approach and Scope
- Build the REST API
- Add authentication
- Write tests

Pricing
Fixed price of $2,000.
"""


# --- renderer ------------------------------------------------------------
def test_parse_proposal_classifies_elements():
    kinds = [kind for kind, _ in parse_proposal(_SAMPLE)]
    assert "heading" in kinds
    assert "bullet" in kinds
    assert "para" in kinds


def test_parse_proposal_detects_markdown_headings():
    elements = parse_proposal("## Why Me\nI am a great fit.")
    assert elements[0] == ("heading", "Why Me")


def test_render_proposal_pdf_returns_pdf_bytes():
    pdf = render_proposal_pdf(
        proposal_text=_SAMPLE,
        job_title="Build a REST API",
        client_name="Acme",
        brand_name="UCT",
    )
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_render_proposal_pdf_handles_unicode():
    # Smart quotes / em dashes must not crash the Latin-1 core fonts.
    pdf = render_proposal_pdf(
        proposal_text="Introduction\nWe’ll deliver — on time — the “best” result.",
        job_title="Tëst Jöb",
    )
    assert pdf[:5] == b"%PDF-"


# --- endpoint ------------------------------------------------------------
def _intake() -> dict:
    return {
        "job_title": "Build a REST API",
        "job_description": "Need a Python REST API.",
        "client_name": "Acme",
    }


def _reach_final(client) -> str:
    session_id = client.post("/api/session/start", json=_intake()).json()["session_id"]
    client.post(f"/api/session/{session_id}/message", json={"message": "/draft"})
    client.post(f"/api/session/{session_id}/message", json={"message": "Approve"})
    return session_id


def test_pdf_export_succeeds_when_final(client):
    session_id = _reach_final(client)
    resp = client.get(f"/api/session/{session_id}/proposal.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content[:5] == b"%PDF-"


def test_pdf_export_rejected_before_final(client):
    session_id = client.post("/api/session/start", json=_intake()).json()["session_id"]
    resp = client.get(f"/api/session/{session_id}/proposal.pdf")
    assert resp.status_code == 409
    assert "error" in resp.json()


def test_pdf_export_unknown_session_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/session/{fake_id}/proposal.pdf")
    assert resp.status_code == 404
