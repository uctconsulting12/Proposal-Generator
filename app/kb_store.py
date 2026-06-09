"""Cloud (MongoDB) storage for knowledge-base documents.

Every document a user uploads — a file or an imported GitHub project — is
stored in MongoDB so it is available from any device the user signs in from.
Two things are persisted per document:

* a row in the ``kb_documents`` collection holding the metadata and the
  already-extracted plain text (the text is what RAG indexes, so keeping it
  on the row means the vector index can be rebuilt on any machine without
  re-parsing the original file), and
* the original file bytes in GridFS (bucket ``kb_files``) so the source can
  be downloaded or re-extracted later.

A document is uniquely identified by ``(user_id, filename)``; re-uploading
the same filename overwrites the previous version. All queries are scoped by
``user_id`` — the multi-tenant isolation boundary — so one account can never
read another's documents.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

from pymongo import ASCENDING

from .config import Settings
from .db import get_db, get_gridfs

_COLLECTION = "kb_documents"
_BUCKET = "kb_files"

_indexed = False


def _docs(settings: Settings):
    global _indexed
    col = get_db(settings)[_COLLECTION]
    if not _indexed:
        col.create_index(
            [("user_id", ASCENDING), ("filename", ASCENDING)], unique=True
        )
        _indexed = True
    return col


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_document(
    settings: Settings,
    *,
    user_id: str,
    filename: str,
    content: bytes,
    text: str,
    description: str,
    source: str = "upload",
    project_name: str = "",
    github_url: str = "",
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Create or replace a knowledge-base document for ``user_id``.

    The original bytes go to GridFS; the extracted ``text`` and all metadata
    go on the ``kb_documents`` row. Returns the stored metadata.
    """
    col = _docs(settings)
    fs = get_gridfs(settings, _BUCKET)

    # Replace any prior version of this filename (bytes + row) so re-uploads
    # don't leave orphaned blobs behind.
    existing = col.find_one({"user_id": user_id, "filename": filename})
    if existing is not None and existing.get("content_id") is not None:
        try:
            fs.delete(existing["content_id"])
        except Exception:  # noqa: BLE001 - a missing blob must not block re-upload
            pass

    content_id = fs.put(content, filename=filename, user_id=user_id)
    meta = {
        "user_id": user_id,
        "filename": filename,
        "description": description,
        "uploaded_at": _now_iso(),
        "size_bytes": len(content),
        "source": source,
        "project_name": project_name,
        "github_url": github_url,
        "topics": list(topics or []),
        "text": text,
        "content_id": content_id,
    }
    col.update_one(
        {"user_id": user_id, "filename": filename},
        {"$set": meta},
        upsert=True,
    )
    return meta


def list_documents(settings: Settings, user_id: str) -> list[dict[str, Any]]:
    """Return this user's documents (metadata only), newest first."""
    cursor = _docs(settings).find(
        {"user_id": user_id},
        {"text": 0, "content_id": 0},  # omit heavy/internal fields
    )
    rows = list(cursor)
    rows.sort(key=lambda r: str(r.get("uploaded_at", "")), reverse=True)
    return rows


def delete_document(settings: Settings, user_id: str, filename: str) -> bool:
    """Delete one document (row + GridFS bytes). Returns True if it existed."""
    col = _docs(settings)
    doc = col.find_one({"user_id": user_id, "filename": filename})
    if doc is None:
        return False
    if doc.get("content_id") is not None:
        try:
            get_gridfs(settings, _BUCKET).delete(doc["content_id"])
        except Exception:  # noqa: BLE001
            pass
    col.delete_one({"_id": doc["_id"]})
    return True


def iter_all_documents(settings: Settings) -> Iterator[dict[str, Any]]:
    """Yield every document across all users for a full vector reindex.

    Each row carries ``user_id`` so the index can stamp ownership on every
    chunk and keep tenants isolated at retrieval time.
    """
    yield from _docs(settings).find({}, {"content_id": 0})


def get_document_bytes(
    settings: Settings, user_id: str, filename: str
) -> bytes | None:
    """Return the original file bytes for a document, or None if absent."""
    doc = _docs(settings).find_one({"user_id": user_id, "filename": filename})
    if doc is None or doc.get("content_id") is None:
        return None
    try:
        return get_gridfs(settings, _BUCKET).get(doc["content_id"]).read()
    except Exception:  # noqa: BLE001
        return None
