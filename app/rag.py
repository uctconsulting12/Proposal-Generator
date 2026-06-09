"""Retrieval-Augmented Generation service.

Indexes the knowledge-base directory into a local Qdrant collection using
fastembed embeddings, and retrieves the most relevant chunks for a query.

All operations are blocking (embedding + vector I/O); callers in async contexts
must dispatch them to a worker thread. A lock serialises index/query access
because the local (embedded) Qdrant client is not safe for concurrent use.
"""

from __future__ import annotations

import logging
import threading
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .config import Settings
from .errors import DependencyUnavailableError

# BGE bi-encoders are trained with this exact prefix on queries. Without it,
# retrieval quality drops noticeably and disproportionately hurts topical
# specificity (the failure mode the user reported).
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Overfetch factor: ask Qdrant for k * this many candidates so the per-source
# diversification step has enough material to produce k distinct projects.
_RETRIEVAL_OVERFETCH = 4
# Cap on how many chunks any single project may contribute to the final set,
# so one verbose README cannot crowd out every other project.
_MAX_CHUNKS_PER_SOURCE = 2

logger = logging.getLogger(__name__)

# Optional heavy dependencies — imported defensively so the module can be
# imported (and unit-tested) even when they are absent.
try:  # pragma: no cover - import guard
    from fastembed import TextEmbedding
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )

    _VECTOR_STACK_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    TextEmbedding = None
    QdrantClient = None
    Distance = PointStruct = VectorParams = None
    FieldCondition = Filter = MatchValue = None
    _VECTOR_STACK_AVAILABLE = False

try:  # pragma: no cover - import guard
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - import guard
    PdfReader = None

_TEXT_SUFFIXES = {".txt", ".md", ".json"}


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping fixed-size chunks."""
    text = text.strip()
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml_data = zf.read("word/document.xml")
    root = ET.fromstring(xml_data)
    return " ".join(
        node.text for node in root.iter() if node.tag.endswith("}t") and node.text
    )


def _extract_pdf(path: Path) -> str:
    if PdfReader is None:
        logger.warning("pypdf not installed; skipping PDF %s", path.name)
        return ""
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text(path: Path) -> str:
    """Extract plain text from a supported knowledge-base file."""
    suffix = path.suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    return ""


class RagService:
    """Owns the embedding model and the Qdrant collection."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.RLock()
        self._embedder = None
        self._client = None
        self._chunk_count = 0

    @property
    def available(self) -> bool:
        """Whether the optional vector dependencies are installed."""
        return _VECTOR_STACK_AVAILABLE

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    def _ensure_stack(self) -> None:
        """Lazily initialise the embedder and vector store. Caller holds lock."""
        if not _VECTOR_STACK_AVAILABLE:
            raise DependencyUnavailableError(
                "Vector dependencies missing. Install: pip install qdrant-client fastembed"
            )
        if self._embedder is None:
            logger.info("Loading embedding model %s", self._settings.embedding_model)
            self._embedder = TextEmbedding(model_name=self._settings.embedding_model)
        if self._client is None:
            self._settings.qdrant_path.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(self._settings.qdrant_path))

    def _recreate_collection(self, vector_size: int) -> None:
        name = self._settings.qdrant_collection
        existing = {c.name for c in self._client.get_collections().collections}
        if name in existing:
            self._client.delete_collection(name)
        self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def reindex(self) -> int:
        """Rebuild the vector index from the cloud (MongoDB) document store.

        Every document a user has uploaded or imported lives in MongoDB (see
        :mod:`app.kb_store`), carrying its already-extracted text and metadata.
        We pull them all and rebuild the local Qdrant index from scratch, so a
        fresh machine that has never seen the original files can still produce
        a complete, up-to-date index purely from the cloud database. The local
        Qdrant store is therefore just a derived cache.

        Each document carries its owner ``user_id``; we stamp it on every chunk
        so retrieval can filter to "only this user's projects" and one tenant's
        portfolio never leaks into another's proposal.
        """
        # Local import avoids a circular dependency (kb_store -> db -> config).
        from . import kb_store

        with self._lock:
            self._ensure_stack()

            raw_chunks: list[dict[str, str]] = []
            for doc in kb_store.iter_all_documents(self._settings):
                owner_id = str(doc.get("user_id") or "")
                if not owner_id:
                    # An unowned document would be retrievable by everyone —
                    # skip rather than leak it across tenants.
                    continue
                text = str(doc.get("text") or "")
                if not text.strip():
                    continue
                filename = str(doc.get("filename") or "document")

                # Mix in stored metadata: the AI-generated description is
                # higher-signal than the raw README (it explicitly names the
                # project type and domain), and prepending it makes topical
                # queries hit the right project even when the README is
                # verbose or off-topic. We also stash project_name /
                # github_url / description on every chunk payload so they
                # survive retrieval and reach the prompt.
                project_name = str(doc.get("project_name") or "")
                github_url = str(doc.get("github_url") or "")
                description = str(doc.get("description") or "")
                header_lines: list[str] = []
                if project_name:
                    header_lines.append(f"Project: {project_name}")
                if github_url:
                    header_lines.append(f"GitHub: {github_url}")
                if description:
                    header_lines.append(f"Summary: {description}")
                indexed_text = (
                    "\n".join(header_lines) + "\n\n" + text if header_lines else text
                )

                for i, part in enumerate(
                    chunk_text(
                        indexed_text,
                        self._settings.chunk_size,
                        self._settings.chunk_overlap,
                    )
                ):
                    raw_chunks.append(
                        {
                            "source": f"{owner_id}/{filename}",
                            "chunk_id": f"{filename}:{i}",
                            "content": part,
                            "project_name": project_name,
                            "github_url": github_url,
                            "description": description,
                            "user_id": owner_id,
                        }
                    )

            if not raw_chunks:
                self._recreate_collection(vector_size=384)
                self._chunk_count = 0
                logger.info("Knowledge base is empty; created empty collection")
                return 0

            vectors = list(self._embedder.embed([c["content"] for c in raw_chunks]))
            self._recreate_collection(vector_size=len(vectors[0]))
            points = [
                PointStruct(id=i + 1, vector=vec.tolist(), payload=chunk)
                for i, (vec, chunk) in enumerate(zip(vectors, raw_chunks))
            ]
            self._client.upsert(
                collection_name=self._settings.qdrant_collection, points=points
            )
            self._chunk_count = len(raw_chunks)
            logger.info("Indexed %d chunk(s) from knowledge base", self._chunk_count)
            return self._chunk_count

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        *,
        user_id: str | None = None,
    ) -> list[dict[str, str]]:
        """Return the top-k knowledge-base chunks most similar to the query.

        Three retrieval tweaks beyond a plain vector search:

        * BGE bi-encoders need the canonical query prefix to score well, so we
          prepend it before embedding (only on the query side — passages are
          embedded as-is, which matches how the index was built).
        * Qdrant is asked for ``top_k * _RETRIEVAL_OVERFETCH`` candidates; we
          then keep at most ``_MAX_CHUNKS_PER_SOURCE`` chunks per source file
          and return the first ``top_k`` results. This stops one verbose
          project README from crowding out every other project, which was the
          root cause of the same chatbot match appearing on every CV job.
        * When ``user_id`` is supplied, a Qdrant payload filter restricts the
          search to chunks owned by that user. This is the multi-tenant
          isolation guarantee — user A can never retrieve user B's projects.
          When ``user_id`` is ``None`` no filter is applied (used by admin
          tooling and tests); production callers must always pass a value.
        """
        query = query.strip()
        if not query:
            return []
        top_k = top_k or self._settings.retrieval_top_k
        prefixed_query = _BGE_QUERY_PREFIX + query
        fetch_limit = max(top_k * _RETRIEVAL_OVERFETCH, top_k)
        query_filter = None
        if user_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id", match=MatchValue(value=str(user_id))
                    )
                ]
            )
        with self._lock:
            self._ensure_stack()
            query_vec = list(self._embedder.embed([prefixed_query]))[0].tolist()
            hits = self._client.query_points(
                collection_name=self._settings.qdrant_collection,
                query=query_vec,
                limit=fetch_limit,
                with_payload=True,
                query_filter=query_filter,
            ).points

        # Diversify by source: walk hits in score order, keep up to
        # _MAX_CHUNKS_PER_SOURCE per source, stop at top_k total.
        results: list[dict[str, str]] = []
        per_source: dict[str, int] = {}
        for hit in hits:
            payload = hit.payload or {}
            source = str(payload.get("source", ""))
            if per_source.get(source, 0) >= _MAX_CHUNKS_PER_SOURCE:
                continue
            per_source[source] = per_source.get(source, 0) + 1
            results.append(
                {
                    "source": source,
                    "chunk_id": str(payload.get("chunk_id", "")),
                    "content": str(payload.get("content", "")),
                    "project_name": str(payload.get("project_name", "")),
                    "github_url": str(payload.get("github_url", "")),
                    "description": str(payload.get("description", "")),
                    "score": round(float(getattr(hit, "score", 0.0)), 4),
                }
            )
            if len(results) >= top_k:
                break
        return results

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:  # noqa: BLE001
                    pass
                self._client = None
