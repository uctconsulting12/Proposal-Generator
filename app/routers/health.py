"""Health and readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import __version__
from ..llm import LlmClient
from ..rag import RagService
from ..schemas import HealthResponse
from ..services import get_llm, get_rag, get_store
from ..storage import MongoSessionStore

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    store: MongoSessionStore = Depends(get_store),
    rag: RagService = Depends(get_rag),
    llm: LlmClient = Depends(get_llm),
) -> HealthResponse:
    """Report service status and the reachability of upstream dependencies."""
    ollama_ok = await llm.ping()
    return HealthResponse(
        status="ok",
        version=__version__,
        sessions=store.count(),
        kb_chunks=rag.chunk_count,
        rag_available=rag.available,
        ollama_reachable=ollama_ok,
    )
