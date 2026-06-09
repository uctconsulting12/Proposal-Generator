"""Application configuration.

All settings are read from environment variables (or a local .env file) so the
same code runs unchanged across environments. See .env.example for the full list.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = directory that contains this package.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="COPILOT_",
        extra="ignore",
    )

    # --- HTTP server -----------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8082
    # The React dev/preview server runs on 5173 by default. Override via
    # COPILOT_CORS_ORIGINS for additional environments.
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )
    request_timeout_s: float = 200.0

    # When True, the FastAPI app additionally serves the built React bundle
    # from ``frontend_dir`` at /. Defaults to False because the React app now
    # runs on its own dev server (port 5173) during development.
    serve_frontend: bool = False

    # --- Authentication --------------------------------------------------
    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60 * 24
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "jd_copilot_auth"

    # --- LLM provider ----------------------------------------------------
    # "ollama" uses a local Ollama server. "gemini" uses Google's Gemini API
    # (requires gemini_api_key). model_name is interpreted per provider, e.g.
    #   ollama:  "qwen3:14b"
    #   gemini:  "gemini-2.5-flash"
    llm_provider: Literal["ollama", "gemini"] = "ollama"
    model_name: str = "qwen3:14b"
    llm_timeout_s: float = 180.0
    llm_max_retries: int = 2

    # Ollama-specific
    ollama_url: str = "http://localhost:11434/api/chat"
    # Embedding model served by the same Ollama host (used for RAG). Running
    # embeddings remotely keeps this process light enough for a 512 MB box.
    ollama_embed_model: str = "nomic-embed-text"

    # Gemini-specific
    gemini_api_key: str = ""
    gemini_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    # --- Paths -----------------------------------------------------------
    # Default points at the production build of the React app
    # (``frontend-react/dist``) so ``serve_frontend=True`` works after
    # ``npm run build`` without extra configuration.
    frontend_dir: Path = BASE_DIR / "frontend-react" / "dist"
    kb_dir: Path = BASE_DIR / "knowledge_base"
    sessions_file: Path = BASE_DIR / "web_sessions.json"
    qdrant_path: Path = BASE_DIR / "qdrant_data"
    # Where per-user company logos live (one sub-directory per user id).
    profiles_dir: Path = BASE_DIR / "profiles"
    # Hard cap on company-logo upload size.
    profile_logo_max_bytes: int = 2 * 1024 * 1024  # 2 MB

    # --- Proposal workflow ----------------------------------------------
    # When True, the copilot asks clarifying questions before drafting.
    # When False, it jumps straight to the short draft proposal.
    enable_questions: bool = False
    # Maximum clarifying questions before the draft is produced (kept minimal).
    max_questions: int = 2
    # Brand / company name printed on the exported proposal PDF ("" = omit).
    pdf_brand_name: str = ""

    # --- RAG -------------------------------------------------------------
    qdrant_collection: str = "proposal_kb"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 900
    chunk_overlap: int = 150
    retrieval_top_k: int = 6

    # --- Session limits --------------------------------------------------
    max_sessions: int = 500
    max_messages_per_session: int = 60
    max_message_chars: int = 8000
    max_jd_chars: int = 40000

    # --- Logging ---------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
