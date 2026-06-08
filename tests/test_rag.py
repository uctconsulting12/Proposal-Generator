"""Tests for RAG helpers that do not require the vector stack."""

from __future__ import annotations

import pytest

from app.prompts import format_rag_context
from app.rag import chunk_text, extract_text


def test_chunk_text_empty_returns_nothing():
    assert chunk_text("", 100, 10) == []


def test_chunk_text_short_text_is_single_chunk():
    assert chunk_text("hello world", 100, 10) == ["hello world"]


def test_chunk_text_splits_with_overlap():
    text = "abcdefghij" * 10  # 100 chars
    chunks = chunk_text(text, chunk_size=40, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 40 for c in chunks)
    # Consecutive chunks share the overlap region.
    assert chunks[0][-10:] == chunks[1][:10]


def test_chunk_text_rejects_overlap_ge_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=10, overlap=10)


def test_extract_text_reads_plain_files(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("project summary", encoding="utf-8")
    assert extract_text(path) == "project summary"


def test_extract_text_unsupported_suffix_returns_empty(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"\x89PNG")
    assert extract_text(path) == ""


def test_format_rag_context_empty():
    assert format_rag_context([]) == ""


def test_format_rag_context_numbers_sources():
    chunks = [
        {"source": "a.txt", "content": "first project details"},
        {"source": "b.txt", "content": "second project details"},
    ]
    rendered = format_rag_context(chunks)
    assert "[1] Past project file: a.txt" in rendered
    assert "[2] Past project file: b.txt" in rendered


def test_format_rag_context_groups_excerpts_by_source():
    chunks = [
        {"source": "proposal_x.pdf", "content": "intro part"},
        {"source": "proposal_x.pdf", "content": "outcome part"},
    ]
    rendered = format_rag_context(chunks)
    # Both excerpts collapse under a single numbered project block.
    assert rendered.count("Past project file:") == 1
    assert "intro part" in rendered and "outcome part" in rendered
