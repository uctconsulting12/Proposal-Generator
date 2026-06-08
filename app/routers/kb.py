"""Knowledge-base management endpoints."""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..auth import require_user
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


def _write_sidecar(target: Path, meta: dict) -> None:
    """Persist KB document metadata next to the original file."""
    meta_path = target.with_suffix(target.suffix + ".meta.json")
    try:
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not write KB metadata sidecar %s: %s", meta_path, exc)


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

    user_dir = settings.kb_dir / "client_uploads" / user["user_id"]
    user_dir.mkdir(parents=True, exist_ok=True)
    target = user_dir / safe_name
    payload = await file.read()
    target.write_bytes(payload)
    await file.close()

    try:
        text = await run_in_threadpool(extract_text, target)
    except Exception:  # noqa: BLE001
        # Fallback extraction for plain text-ish files.
        if suffix in {".txt", ".md", ".json"}:
            text = target.read_text(encoding="utf-8", errors="ignore")
        else:
            text = ""

    description = await _describe_document(llm, safe_name, text)

    indexed = False
    chunk_count: int | None = None
    if rag.available:
        try:
            chunk_count = await run_in_threadpool(rag.reindex)
            indexed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reindex after upload failed: %s", exc)

    rel = str(target.relative_to(settings.kb_dir))

    # Sidecar metadata so the Client Database listing can show the description
    # without re-running the LLM on every page load. Additive: it never alters
    # the upload contract or the indexed file content.
    _write_sidecar(
        target,
        {
            "filename": safe_name,
            "description": description,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(payload),
            "source": "upload",
        },
    )

    return KbUploadResponse(
        ok=True,
        filename=safe_name,
        relative_path=rel,
        description=description,
        indexed=indexed,
        kb_chunks=chunk_count,
    )


@router.get("/list", response_model=KbListResponse)
async def list_documents(
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> KbListResponse:
    """List documents this user has uploaded to the KB."""
    user_dir = settings.kb_dir / "client_uploads" / user["user_id"]
    if not user_dir.exists():
        return KbListResponse(documents=[])

    documents: list[KbDocument] = []
    for entry in sorted(user_dir.iterdir()):
        if not entry.is_file() or entry.name.endswith(".meta.json"):
            continue
        meta_path = entry.with_suffix(entry.suffix + ".meta.json")
        description = ""
        uploaded_at = ""
        size_bytes = 0
        source = "upload"
        project_name = ""
        github_url = ""
        topics: list[str] = []
        try:
            stat = entry.stat()
            size_bytes = stat.st_size
            uploaded_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            pass
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                description = str(meta.get("description", "")) or description
                uploaded_at = str(meta.get("uploaded_at", "")) or uploaded_at
                size_bytes = int(meta.get("size_bytes", size_bytes) or size_bytes)
                source = str(meta.get("source", source))
                project_name = str(meta.get("project_name", ""))
                github_url = str(meta.get("github_url", ""))
                raw_topics = meta.get("topics", [])
                if isinstance(raw_topics, list):
                    topics = [str(t) for t in raw_topics]
            except (OSError, json.JSONDecodeError):
                pass
        documents.append(
            KbDocument(
                filename=entry.name,
                relative_path=str(entry.relative_to(settings.kb_dir)),
                description=description or "(No description available — re-upload to generate one.)",
                size_bytes=size_bytes,
                uploaded_at=uploaded_at,
                source=source,
                project_name=project_name,
                github_url=github_url,
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

    user_dir = settings.kb_dir / "client_uploads" / user["user_id"]
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(f"github_{owner}_{repo}.md")
    target = user_dir / safe_name
    target.write_text(body, encoding="utf-8")

    description = await _describe_document(llm, safe_name, body)

    indexed = False
    chunk_count: int | None = None
    if rag.available:
        try:
            chunk_count = await run_in_threadpool(rag.reindex)
            indexed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reindex after GitHub import failed: %s", exc)

    _write_sidecar(
        target,
        {
            "filename": safe_name,
            "description": description,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(body.encode("utf-8")),
            "source": "github",
            "project_name": project_name,
            "github_url": github_url,
            "topics": topics,
        },
    )

    rel = str(target.relative_to(settings.kb_dir))
    return KbUploadResponse(
        ok=True,
        filename=safe_name,
        relative_path=rel,
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
    """Remove a document (and its .meta.json sidecar) from this user's KB.

    The filename is constrained to a single path component under the
    caller's own ``client_uploads/<user_id>/`` directory; the resolved
    target must stay inside that directory or the request is rejected as
    a path-traversal attempt. A reindex follows so the vector store stops
    returning the deleted chunks.
    """
    safe_name = _safe_filename(filename)
    user_dir = (settings.kb_dir / "client_uploads" / user["user_id"]).resolve()
    if not user_dir.exists():
        raise NotFoundError("Document not found")

    target = (user_dir / safe_name).resolve()
    # Path-traversal guard: the resolved target must be a direct child of
    # the user's own directory. Reject symlinks, ".." escapes, anything
    # outside that scope.
    try:
        target.relative_to(user_dir)
    except ValueError as exc:
        raise AppError("Invalid filename", status_code=400) from exc
    if target.parent != user_dir:
        raise AppError("Invalid filename", status_code=400)
    if not target.is_file():
        raise NotFoundError("Document not found")

    meta_path = target.with_suffix(target.suffix + ".meta.json")
    try:
        target.unlink()
    except OSError as exc:
        raise AppError(f"Could not delete file: {exc}", status_code=500) from exc
    if meta_path.exists():
        try:
            meta_path.unlink()
        except OSError as exc:
            logger.warning("Could not delete sidecar %s: %s", meta_path, exc)

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
