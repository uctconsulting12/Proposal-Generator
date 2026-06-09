"""Knowledge-base management endpoints."""

from __future__ import annotations

import base64
import logging
import re
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..auth import require_user
from .. import kb_store
from ..errors import AppError, DependencyUnavailableError, NotFoundError, UpstreamError
from ..llm import LlmClient
from ..rag import RagService, extract_text
from ..schemas import (
    GithubImportRequest,
    KbDeleteResponse,
    KbDocument,
    KbListResponse,
    KbUploadResponse,
    ReindexResponse,
)
from ..services import get_llm, get_rag, get_settings_dep
from ..config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])
_ALLOWED_SUFFIXES = {".txt", ".md", ".json", ".pdf", ".docx"}


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return cleaned or "upload.txt"


def _extract_text_from_bytes(payload: bytes, suffix: str) -> str:
    """Extract plain text from uploaded bytes.

    ``extract_text`` works off a file path (it sniffs the suffix and uses the
    right parser for PDF/DOCX), so we stage the bytes in a temporary file,
    extract, then discard it. Nothing is persisted to local disk — the bytes
    of record live in MongoDB/GridFS.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        try:
            return extract_text(tmp_path)
        except Exception:  # noqa: BLE001
            if suffix in {".txt", ".md", ".json"}:
                return payload.decode("utf-8", errors="ignore")
            return ""
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL or raise AppError."""
    cleaned = url.strip().rstrip("/")
    match = _GITHUB_URL_RE.match(cleaned)
    if not match:
        raise AppError("Invalid GitHub URL. Expected https://github.com/<owner>/<repo>", status_code=400)
    return match.group("owner"), match.group("repo")


async def _fetch_github_repo(owner: str, repo: str) -> dict:
    """Fetch repo metadata from GitHub's REST API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "JD-Proposal-Copilot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
        )
    if res.status_code == 404:
        raise AppError(f"GitHub repo not found: {owner}/{repo}", status_code=404)
    if res.status_code != 200:
        raise UpstreamError(f"GitHub API error ({res.status_code})")
    return res.json()


async def _fetch_github_readme(owner: str, repo: str) -> str:
    """Fetch the default README from a GitHub repo; '' if none exists."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "JD-Proposal-Copilot",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=headers,
        )
    if res.status_code == 404:
        return ""
    if res.status_code != 200:
        raise UpstreamError(f"GitHub README fetch error ({res.status_code})")
    data = res.json()
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            return ""
    return str(data.get("content", ""))


def _fallback_description(filename: str, text: str) -> str:
    compact = " ".join(text.split())
    preview = compact[:280]
    if len(compact) > 280:
        preview += "..."
    return (
        f"Document '{filename}' uploaded successfully. "
        f"Extracted ~{len(text)} characters. Preview: {preview or 'No readable text found.'}"
    )


async def _describe_document(llm: LlmClient, filename: str, text: str) -> str:
    snippet = text[:5000]
    if not snippet.strip():
        return f"Document '{filename}' appears to contain no extractable text."
    prompt = (
        "Summarize this past proposal/project document for a freelancer knowledge base.\n"
        "Return 4-6 concise bullet points covering project type, scope, tech stack, "
        "business outcome, and notable delivery constraints.\n\n"
        f"Filename: {filename}\n"
        f"Document text:\n{snippet}"
    )
    try:
        return await llm.chat(
            [
                {
                    "role": "system",
                    "content": "You are a precise analyst for proposal knowledge-base documents.",
                },
                {"role": "user", "content": prompt},
            ]
        )
    except Exception:  # noqa: BLE001 - user should still get a usable response
        return _fallback_description(filename, text)


@router.post("/reindex", response_model=ReindexResponse)
async def reindex(rag: RagService = Depends(get_rag)) -> ReindexResponse:
    """Rebuild the vector index from the knowledge-base directory."""
    if not rag.available:
        raise DependencyUnavailableError(
            "Vector dependencies are not installed; cannot reindex."
        )
    try:
        count = await run_in_threadpool(rag.reindex)
    except DependencyUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reindex failed")
        raise UpstreamError(f"Reindex failed: {exc}") from exc
    return ReindexResponse(ok=True, kb_chunks=count)


@router.post("/upload", response_model=KbUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings_dep),
    rag: RagService = Depends(get_rag),
    llm: LlmClient = Depends(get_llm),
    user: dict[str, str] = Depends(require_user),
) -> KbUploadResponse:
    """Upload a proposal document, describe it instantly, and save to KB."""
    original = file.filename or "upload.txt"
    safe_name = _safe_filename(original)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        allowed = ", ".join(sorted(_ALLOWED_SUFFIXES))
        raise AppError(
            f"Unsupported file type '{suffix or '(none)'}'. Allowed: {allowed}",
            status_code=400,
        )

    payload = await file.read()
    await file.close()

    text = await run_in_threadpool(_extract_text_from_bytes, payload, suffix)
    description = await _describe_document(llm, safe_name, text)

    # Persist to the cloud (MongoDB): bytes to GridFS, text + metadata to the
    # kb_documents collection. This is the source of truth — the same upload
    # is now visible to this user from any device they sign in from.
    await run_in_threadpool(
        kb_store.save_document,
        settings,
        user_id=user["user_id"],
        filename=safe_name,
        content=payload,
        text=text,
        description=description,
        source="upload",
    )

    indexed = False
    chunk_count: int | None = None
    if rag.available:
        try:
            chunk_count = await run_in_threadpool(rag.reindex)
            indexed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reindex after upload failed: %s", exc)

    return KbUploadResponse(
        ok=True,
        filename=safe_name,
        relative_path=f"{user['user_id']}/{safe_name}",
        description=description,
        indexed=indexed,
        kb_chunks=chunk_count,
    )


@router.get("/list", response_model=KbListResponse)
async def list_documents(
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> KbListResponse:
    """List documents this user has uploaded to the KB (from the cloud DB)."""
    rows = await run_in_threadpool(kb_store.list_documents, settings, user["user_id"])

    documents: list[KbDocument] = []
    for meta in rows:
        raw_topics = meta.get("topics", [])
        topics = [str(t) for t in raw_topics] if isinstance(raw_topics, list) else []
        filename = str(meta.get("filename", ""))
        documents.append(
            KbDocument(
                filename=filename,
                relative_path=f"{user['user_id']}/{filename}",
                description=str(meta.get("description", ""))
                or "(No description available — re-upload to generate one.)",
                size_bytes=int(meta.get("size_bytes", 0) or 0),
                uploaded_at=str(meta.get("uploaded_at", "")),
                source=str(meta.get("source", "upload")),
                project_name=str(meta.get("project_name", "")),
                github_url=str(meta.get("github_url", "")),
                topics=topics,
            )
        )

    documents.sort(key=lambda d: d.uploaded_at, reverse=True)
    return KbListResponse(documents=documents)


@router.post("/github", response_model=KbUploadResponse)
async def add_github_project(
    payload: GithubImportRequest,
    settings: Settings = Depends(get_settings_dep),
    rag: RagService = Depends(get_rag),
    llm: LlmClient = Depends(get_llm),
    user: dict[str, str] = Depends(require_user),
) -> KbUploadResponse:
    """Import a public GitHub project: fetch metadata + README, store in KB."""
    owner, repo = _parse_github_url(payload.github_url)
    repo_info = await _fetch_github_repo(owner, repo)
    readme_text = await _fetch_github_readme(owner, repo)

    project_name = str(repo_info.get("name") or repo)
    github_url = str(repo_info.get("html_url") or payload.github_url)
    repo_description = str(repo_info.get("description") or "")
    topics = repo_info.get("topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [str(t) for t in topics]

    # Compose the file body so RAG can retrieve from project name + topics + README.
    header = (
        f"# {project_name}\n\n"
        f"GitHub: {github_url}\n"
        f"Repo description: {repo_description or '(none)'}\n"
        f"Topics: {', '.join(topics) if topics else '(none)'}\n\n"
        "---\n\n"
    )
    body = header + (readme_text or "(No README found on GitHub.)")
    safe_name = _safe_filename(f"github_{owner}_{repo}.md")

    description = await _describe_document(llm, safe_name, body)

    # Persist the imported project to the cloud (MongoDB) just like an upload.
    await run_in_threadpool(
        kb_store.save_document,
        settings,
        user_id=user["user_id"],
        filename=safe_name,
        content=body.encode("utf-8"),
        text=body,
        description=description,
        source="github",
        project_name=project_name,
        github_url=github_url,
        topics=topics,
    )

    indexed = False
    chunk_count: int | None = None
    if rag.available:
        try:
            chunk_count = await run_in_threadpool(rag.reindex)
            indexed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reindex after GitHub import failed: %s", exc)

    return KbUploadResponse(
        ok=True,
        filename=safe_name,
        relative_path=f"{user['user_id']}/{safe_name}",
        description=description,
        indexed=indexed,
        kb_chunks=chunk_count,
    )


@router.delete("/document", response_model=KbDeleteResponse)
async def delete_document(
    filename: str = Query(..., min_length=1, max_length=300),
    settings: Settings = Depends(get_settings_dep),
    rag: RagService = Depends(get_rag),
    user: dict[str, str] = Depends(require_user),
) -> KbDeleteResponse:
    """Remove a document from this user's KB in the cloud (MongoDB).

    The document is looked up by ``(user_id, filename)`` so a user can only
    ever delete their own documents — there is no shared filesystem and no
    path to traverse. A reindex follows so the vector store stops returning
    the deleted chunks.
    """
    safe_name = _safe_filename(filename)
    deleted = await run_in_threadpool(
        kb_store.delete_document, settings, user["user_id"], safe_name
    )
    if not deleted:
        raise NotFoundError("Document not found")

    indexed = False
    chunk_count: int | None = None
    if rag.available:
        try:
            chunk_count = await run_in_threadpool(rag.reindex)
            indexed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reindex after delete failed: %s", exc)

    logger.info("Deleted KB document %s for user %s", safe_name, user["user_id"])
    return KbDeleteResponse(
        ok=True,
        filename=safe_name,
        indexed=indexed,
        kb_chunks=chunk_count,
    )
