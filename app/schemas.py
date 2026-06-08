"""Pydantic request/response models.

These define and enforce the API contract: every inbound payload is validated
and every response is a typed model, so the frontend has a stable schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .config import get_settings

_settings = get_settings()


class JDIntake(BaseModel):
    """Job-description intake submitted when a session starts."""

    # Limits are generous: they exist to bound payload size, not to reject
    # normal pasted intake content. The job description gets the largest budget.
    client_name: str = Field("", max_length=1000)
    job_title: str = Field(..., min_length=1, max_length=1000)
    job_description: str = Field(..., min_length=1, max_length=_settings.max_jd_chars)
    budget: str = Field("", max_length=1000)
    timeline: str = Field("", max_length=1000)
    tech_stack: str = Field("", max_length=2000)
    deliverables: str = Field("", max_length=20000)
    constraints: str = Field("", max_length=20000)

    @field_validator("job_title", "job_description")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


# Conversation stages.
STAGE_QUESTIONING = "questioning"
STAGE_DRAFT = "draft"
STAGE_FINAL = "final"


class StartSessionResponse(BaseModel):
    session_id: str
    assistant: str
    retrieved_sources: list[str]
    stage: str


class SessionSummary(BaseModel):
    session_id: str
    job_title: str
    stage: str
    closed: bool
    created_at: str
    updated_at: str


class SessionMessage(BaseModel):
    role: str
    content: str


class SessionDetailResponse(BaseModel):
    session_id: str
    stage: str
    closed: bool
    job_title: str
    intake: dict[str, str]
    messages: list[SessionMessage]


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=_settings.max_message_chars)

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value.strip()


class MessageResponse(BaseModel):
    assistant: str
    stage: str


class FinalizeResponse(BaseModel):
    ok: bool
    closed: bool


class ReindexResponse(BaseModel):
    ok: bool
    kb_chunks: int


class KbUploadResponse(BaseModel):
    ok: bool
    filename: str
    relative_path: str
    description: str
    indexed: bool
    kb_chunks: int | None = None


class KbDocument(BaseModel):
    filename: str
    relative_path: str
    description: str
    size_bytes: int
    uploaded_at: str
    # GitHub-sourced documents carry extra metadata so the Client Database UI
    # can render the project link, topics, and project name as a card.
    source: str = "upload"  # "upload" | "github"
    project_name: str = ""
    github_url: str = ""
    topics: list[str] = Field(default_factory=list)


class KbListResponse(BaseModel):
    documents: list[KbDocument]


class KbDeleteResponse(BaseModel):
    """Response for a successful document deletion + reindex."""

    ok: bool
    filename: str
    indexed: bool
    kb_chunks: int | None = None


class GithubImportRequest(BaseModel):
    """Add a GitHub project to the KB by URL (README fetched automatically)."""

    github_url: str = Field(..., min_length=10, max_length=500)

    @field_validator("github_url")
    @classmethod
    def _validate_github_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if "github.com/" not in cleaned:
            raise ValueError("must be a github.com URL")
        return cleaned


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=6, max_length=200)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("email must be valid")
        return value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class MeResponse(BaseModel):
    user_id: str
    email: str


class ProfileResponse(BaseModel):
    """Per-user company profile used to brand proposals."""

    company_name: str = ""
    company_intro: str = ""
    intro_verbatim: bool = False
    signature: str = ""
    accent_color: str = "#0f766e"
    template_id: str = "modern"
    has_logo: bool = False
    logo_mime: str = ""
    logo_updated_at: str = ""
    updated_at: str = ""


class ProfileUpdateRequest(BaseModel):
    """Partial profile update — any field left None is unchanged."""

    company_name: str | None = Field(None, max_length=200)
    company_intro: str | None = Field(None, max_length=2000)
    intro_verbatim: bool | None = None
    signature: str | None = Field(None, max_length=200)
    accent_color: str | None = Field(None, max_length=9)
    template_id: str | None = Field(None, max_length=64)


class TemplateInfoResponse(BaseModel):
    id: str
    name: str
    description: str
    tagline: str


class TemplateListResponse(BaseModel):
    templates: list[TemplateInfoResponse]
    default_id: str


class HealthResponse(BaseModel):
    status: str
    version: str
    sessions: int
    kb_chunks: int
    rag_available: bool
    ollama_reachable: bool
