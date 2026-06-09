"""Proposal-copilot session endpoints.

A session moves through stages:

  questioning  -> the copilot asks a few minimal clarifying questions
  draft        -> the copilot shows a short draft proposal and waits for the
                  user to "approve" (or give feedback to revise it)
  final        -> the user approved; the full proposal is generated, after
                  which the chat continues freely for tweaks

The questioning stage is skipped entirely when ``enable_questions`` is False.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, Path, Query, Response
from fastapi.concurrency import run_in_threadpool

from ..config import Settings
from ..auth import require_user
from ..errors import AppError, DependencyUnavailableError, NotFoundError
from ..llm import LlmClient
from ..pdf import render_proposal_pdf
from ..prompts import (
    ASK_QUESTION,
    DRAFT_PROPOSAL,
    EDIT_PROPOSAL,
    FINAL_PROPOSAL,
    QA_INSTRUCTION,
    REGENERATE_PROPOSAL,
    build_system_prompt,
    control_turn,
    format_rag_context,
    revise_draft_instruction,
)
from ..rag import RagService
from .. import profiles as profile_store
from ..schemas import (
    STAGE_DRAFT,
    STAGE_FINAL,
    STAGE_QUESTIONING,
    FinalizeResponse,
    JDIntake,
    MessageRequest,
    MessageResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionMessage,
    StartSessionResponse,
)
from ..services import get_llm, get_rag, get_settings_dep, get_store
from ..storage import MongoSessionStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/session", tags=["sessions"])

_SESSION_ID = Path(..., pattern=r"^[0-9a-fA-F-]{36}$", description="Session UUID")

# Words that, when present in a STAGE_FINAL turn, mean "rewrite the whole
# proposal" rather than "edit it". Used by _classify_final_intent below.
_REGEN_RE = re.compile(
    r"\b(regenerate|rewrite|redo|regen|start over|do[\- ]over|do it again)\b",
    re.IGNORECASE,
)
# Heuristic for question-shaped turns the user wants ANSWERED, not edits
# applied to the proposal. Matched only when the message is short (otherwise
# longer "Why X and could you also Y?" tends to mean an edit).
_QA_RE = re.compile(
    r"^(what|how|why|when|where|who|which|is\b|are\b|does\b|do\b|can\b|could\b|should\b|explain)",
    re.IGNORECASE,
)


def _classify_final_intent(text: str) -> str:
    """Decide whether a post-approval message is a regenerate / edit / question.

    Returns one of: ``"regenerate"``, ``"edit"``, ``"question"``. The default
    is ``"edit"`` because the user has more often been giving change requests
    in this stage than asking lookup questions.
    """
    cleaned = text.strip()
    if not cleaned:
        return "edit"
    if _REGEN_RE.search(cleaned):
        return "regenerate"
    # Short, question-shaped messages without imperative verbs are looked up,
    # not applied as edits.
    if len(cleaned.split()) <= 18 and _QA_RE.match(cleaned) and cleaned.endswith("?"):
        return "question"
    return "edit"


# Marker that begins the portfolio attachment block emitted by the frontend's
# Approve action. We slice on it so subsequent regenerations can re-inject
# the same GitHub-link instructions without keeping the whole approval
# message in the context window.
_PORTFOLIO_ATTACHMENT_MARKER = "[Instruction to assistant: when citing"
# The second "[Instruction to assistant:" inside an approve message is the
# FINAL_PROPOSAL directive wrapper appended by control_turn — we want to
# stop the portfolio extraction right before it so we don't also smuggle
# the stale FINAL_PROPOSAL block forward.
_DIRECTIVE_PREFIX = "[Instruction to assistant:"


def _extract_portfolio_attachment(approve_text: str) -> str:
    """Pull the portfolio-bullets block out of an approve message body.

    The frontend composes the approve message as
    ``approve\\n\\n[Instruction to assistant: when citing ...]\\n- [name](url)\\n...``
    and then ``control_turn`` appends a trailing
    ``[Instruction to assistant: FINAL_PROPOSAL...]`` directive. We want
    only the user-attached portfolio block — the FINAL_PROPOSAL directive
    is re-injected separately on later turns and shouldn't be persisted.
    """
    start = approve_text.find(_PORTFOLIO_ATTACHMENT_MARKER)
    if start < 0:
        return ""
    # Search for the next "[Instruction to assistant:" after the portfolio
    # marker — that's the FINAL_PROPOSAL wrapper boundary.
    after = approve_text.find(_DIRECTIVE_PREFIX, start + len(_PORTFOLIO_ATTACHMENT_MARKER))
    block = approve_text[start:after] if after > 0 else approve_text[start:]
    return block.strip()


def _anchor_window(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return ``[system, latest_assistant]`` for post-approval calls.

    The single most-impactful drift-mitigation we have. After the first
    FINAL_PROPOSAL we never give the LLM more than the original intake +
    the most recent proposal anymore — so the 8-section structure and the
    no-invention rule stay dominant no matter how many edit/regenerate
    cycles the user runs.
    """
    sys_msg = next((m for m in history if m.get("role") == "system"), None)
    anchor = next(
        (m for m in reversed(history) if m.get("role") == "assistant"),
        None,
    )
    return [m for m in (sys_msg, anchor) if m is not None]


# Words/commands that count as approving the draft.
_APPROVAL_WORDS = {
    "approve", "approved", "approve it", "yes", "ok", "okay", "go",
    "go ahead", "lgtm", "looks good", "send it", "finalize",
}
# Commands that skip remaining questions and jump to the draft.
_SKIP_TO_DRAFT = {"draft", "finalize", "skip"}


def _is_approval(text: str) -> bool:
    cleaned = text.strip().lower().rstrip(".!")
    return cleaned in _APPROVAL_WORDS or cleaned.startswith("approve")


def _wants_draft_now(text: str) -> bool:
    return text.strip().lower().lstrip("/") in _SKIP_TO_DRAFT


async def _retrieve_context(
    rag: RagService, query: str, *, user_id: str
) -> list[dict[str, str]]:
    """Retrieve KB context for ``user_id`` only, degrading gracefully.

    ``user_id`` is mandatory: it is the multi-tenant isolation boundary, so
    we never call ``rag.retrieve`` without it on user-facing code paths.
    """
    if not rag.available:
        return []
    try:
        return await run_in_threadpool(
            lambda: rag.retrieve(query, user_id=user_id)
        )
    except DependencyUnavailableError:
        return []
    except Exception as exc:  # noqa: BLE001 - retrieval must not break a session
        logger.warning("Retrieval failed, continuing without context: %s", exc)
        return []


# Words that signal the user typed a role / hiring blurb in the title field
# instead of a project name. When any of these appear we always re-derive a
# cover title, even if the LLM-cached value is missing.
_ROLE_TITLE_HINTS = (
    "engineer", "developer", "freelancer", "consultant", "specialist",
    "expert", "architect", "designer", "needed", "required", "wanted",
    "looking for", "looking-for", "hire", "hiring",
)

# Hard cap so the cover title never wraps to three lines or pushes the
# subtitle off the page.
_MAX_PDF_TITLE_CHARS = 70


def _looks_like_role_title(title: str) -> bool:
    """Return True if ``title`` reads as a role/JD posting headline rather
    than a deliverable / project name suitable for a proposal cover."""
    lowered = title.lower()
    if any(hint in lowered for hint in _ROLE_TITLE_HINTS):
        return True
    # Single-word or very short titles ("CV", "ML", "Backend") rarely
    # describe the work.
    if len(title.split()) < 3:
        return True
    return False


async def _derive_pdf_title(
    llm: LlmClient, job_title: str, job_description: str
) -> str:
    """Ask the LLM for a proposal-ready cover title for ``job_description``.

    The model is instructed to return the user's ``job_title`` unchanged
    when it already names what's being delivered, and otherwise to write
    a concise project-noun headline. The returned string is post-processed
    to strip surrounding quotes and trailing punctuation, and falls back
    to the original title on any failure so PDF export can never break
    because of this enrichment step.
    """
    job_title = (job_title or "").strip()
    jd = (job_description or "").strip()
    if not jd:
        return job_title
    if job_title and not _looks_like_role_title(job_title) and len(job_title) <= _MAX_PDF_TITLE_CHARS:
        return job_title

    instruction = (
        "You are titling a client-facing proposal PDF. Read the Job "
        "Description and produce ONE concise cover title (max "
        f"{_MAX_PDF_TITLE_CHARS} characters) naming the deliverable / "
        "project we are proposing to build.\n\n"
        "Rules:\n"
        "- Project-noun focused, not role-focused. 'AI Theft Detection "
        "System for Retail' is good; 'Computer Vision Engineer' is bad.\n"
        "- Title case, no quotes, no trailing punctuation, no emoji.\n"
        "- If the user-supplied title below already names the deliverable "
        "clearly, return it UNCHANGED.\n"
        "- Output ONLY the title text on a single line. No preamble, no "
        "explanation, no markdown.\n\n"
        f"User-supplied title (may be role-shaped):\n{job_title or '(none)'}\n\n"
        f"Job Description:\n{jd[:1500]}"
    )
    try:
        raw = await llm.chat(
            [
                {
                    "role": "system",
                    "content": "You write concise proposal cover titles. One line of plain text, nothing else.",
                },
                {"role": "user", "content": instruction},
            ]
        )
    except Exception as exc:  # noqa: BLE001 - never break PDF export
        logger.warning("PDF title derivation failed, using user title: %s", exc)
        return job_title

    title = raw.strip().splitlines()[0].strip()
    # Strip surrounding quotes the model sometimes wraps the answer in.
    if len(title) >= 2 and title[0] in "\"'" and title[-1] in "\"'":
        title = title[1:-1].strip()
    title = title.rstrip(".!:;-")
    if len(title) > _MAX_PDF_TITLE_CHARS:
        title = title[:_MAX_PDF_TITLE_CHARS].rsplit(" ", 1)[0]
    return title or job_title


def _squash_history_for_final(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Trim chat history to ``[system, latest_draft]`` for the final pass.

    Long draft-revision chains drift the model toward whatever casual tone
    the user iterated toward and away from the strict ``FINAL_PROPOSAL``
    spec — the model averages all prior turns and the spec loses. For the
    one LLM call that generates the final proposal we hand it only the
    original system prompt (intake + RAG context) and the most recent
    assistant draft, then append the new ``approve + FINAL_PROPOSAL`` user
    turn. The full conversation is still persisted to the store untouched,
    so the chat UI keeps the complete history; only the LLM-facing window
    is squashed for this single call.
    """
    system_msg = next((m for m in history if m.get("role") == "system"), None)
    latest_assistant = next(
        (m for m in reversed(history) if m.get("role") == "assistant"),
        None,
    )
    trimmed: list[dict[str, str]] = []
    if system_msg is not None:
        trimmed.append(system_msg)
    if latest_assistant is not None:
        trimmed.append(latest_assistant)
    return trimmed


@router.post("/start", response_model=StartSessionResponse)
async def start_session(
    intake: JDIntake,
    store: MongoSessionStore = Depends(get_store),
    llm: LlmClient = Depends(get_llm),
    rag: RagService = Depends(get_rag),
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> StartSessionResponse:
    """Create a session and produce the first turn (a question or a draft)."""
    # Focused retrieval query: a long JD body dilutes the pooled embedding and
    # pulls every match toward a generic "AI project" centroid. Title + tech
    # stack + the JD's opening (where the topic usually lives) keeps the query
    # vector topical so CV jobs hit CV projects and extraction jobs hit
    # document-intelligence projects.
    query = (
        f"{intake.job_title}\n"
        f"{intake.tech_stack}\n"
        f"{intake.job_description[:500]}"
    )
    retrieved = await _retrieve_context(rag, query, user_id=user["user_id"])
    profile = await run_in_threadpool(
        profile_store.get_profile, settings, user["user_id"]
    )
    system_prompt = build_system_prompt(
        intake, format_rag_context(retrieved), profile=profile
    )

    if settings.enable_questions:
        stage, instruction = STAGE_QUESTIONING, ASK_QUESTION
    else:
        stage, instruction = STAGE_DRAFT, DRAFT_PROPOSAL

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": control_turn("", instruction)},
    ]
    assistant = await llm.chat(messages)
    messages.append({"role": "assistant", "content": assistant})

    session_id = store.create(
        user_id=user["user_id"],
        intake=intake.model_dump(),
        messages=messages,
        retrieved_chunks=retrieved,
        stage=stage,
    )
    logger.info("Started session %s at stage '%s'", session_id, stage)
    return StartSessionResponse(
        session_id=session_id,
        assistant=assistant,
        retrieved_sources=[c["source"] for c in retrieved],
        stage=stage,
    )


@router.post("/{session_id}/message", response_model=MessageResponse)
async def post_message(
    payload: MessageRequest,
    session_id: str = _SESSION_ID,
    store: MongoSessionStore = Depends(get_store),
    llm: LlmClient = Depends(get_llm),
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> MessageResponse:
    """Advance the session by one turn, honouring the current stage."""
    session = store.get(session_id)
    if session is None:
        raise NotFoundError("Session not found")
    if session.get("user_id") != user["user_id"]:
        raise NotFoundError("Session not found")

    stage = session.get("stage", STAGE_FINAL)
    questions_asked = session.get("questions_asked", 0)
    history = list(session["messages"])
    user_text = payload.message

    new_questions_asked = questions_asked
    # By default the LLM sees the full chat history. The approval branch
    # below overrides this with a squashed window so draft-revision drift
    # cannot bleed into the final proposal.
    llm_history = history

    # Portfolio attachment persisted from the approve turn (re-injected on
    # every later edit/regenerate so the GitHub-link constraint survives).
    portfolio_attachment = str(session.get("portfolio_attachment", "")).strip()

    if session.get("closed"):
        # Finalized sessions become Q&A mode. We use the anchored window
        # (system + latest proposal only) so even after dozens of follow-up
        # questions the model still answers grounded in the actual proposal
        # rather than hallucinating from drifting context.
        new_stage = STAGE_FINAL
        llm_history = _anchor_window(history)
        composed = control_turn(user_text, QA_INSTRUCTION)
    elif stage == STAGE_QUESTIONING:
        new_questions_asked = questions_asked + 1
        if _wants_draft_now(user_text) or new_questions_asked >= settings.max_questions:
            new_stage, instruction = STAGE_DRAFT, DRAFT_PROPOSAL
        else:
            new_stage, instruction = STAGE_QUESTIONING, ASK_QUESTION
        composed = control_turn(user_text, instruction)

    elif stage == STAGE_DRAFT:
        if _is_approval(user_text):
            new_stage, instruction = STAGE_FINAL, FINAL_PROPOSAL
            # See _squash_history_for_final docstring.
            llm_history = _squash_history_for_final(history)
            # Persist the portfolio block from the approve message so later
            # edit/regenerate turns can re-attach it without keeping the
            # whole approval turn in context.
            extracted = _extract_portfolio_attachment(user_text)
            if extracted:
                try:
                    store.set_field(session_id, "portfolio_attachment", extracted)
                except KeyError:
                    pass
                portfolio_attachment = extracted
        else:
            new_stage = STAGE_DRAFT
            instruction = revise_draft_instruction(user_text)
        composed = control_turn(user_text, instruction)

    else:  # STAGE_FINAL — anchored-window regenerate / edit / question.
        new_stage = STAGE_FINAL
        llm_history = _anchor_window(history)
        intent = _classify_final_intent(user_text)
        if intent == "regenerate":
            # Body = portfolio attachment only; the literal word "regenerate"
            # carries no useful signal for the model.
            instruction = REGENERATE_PROPOSAL
            body = portfolio_attachment
        elif intent == "question":
            instruction = QA_INSTRUCTION
            body = user_text
        else:  # edit
            instruction = EDIT_PROPOSAL
            body = user_text
            if portfolio_attachment:
                body = f"{body}\n\n{portfolio_attachment}"
        composed = control_turn(body, instruction)

    llm_history.append({"role": "user", "content": composed})
    assistant = await llm.chat(llm_history)

    try:
        store.append_turn(
            session_id,
            composed,
            assistant,
            stage=new_stage,
            questions_asked=new_questions_asked,
        )
    except KeyError:
        # Session was evicted between read and write; surface as not found.
        raise NotFoundError("Session not found") from None

    logger.info("Session %s: stage '%s' -> '%s'", session_id, stage, new_stage)
    return MessageResponse(assistant=assistant, stage=new_stage)


@router.post("/{session_id}/finalize", response_model=FinalizeResponse)
async def finalize_session(
    session_id: str = _SESSION_ID,
    store: MongoSessionStore = Depends(get_store),
    user: dict[str, str] = Depends(require_user),
) -> FinalizeResponse:
    """Finalize a session: lock it so no further messages can be sent."""
    session = store.get(session_id)
    if session is None or session.get("user_id") != user["user_id"]:
        raise NotFoundError("Session not found")
    try:
        store.finalize(session_id)
    except KeyError:
        raise NotFoundError("Session not found") from None
    logger.info("Session %s finalized", session_id)
    return FinalizeResponse(ok=True, closed=True)


@router.delete("/{session_id}", response_model=FinalizeResponse)
async def delete_session(
    session_id: str = _SESSION_ID,
    store: MongoSessionStore = Depends(get_store),
    user: dict[str, str] = Depends(require_user),
) -> FinalizeResponse:
    """Discard a session entirely (the Save/Discard prompt's Discard path)."""
    session = store.get(session_id)
    if session is None or session.get("user_id") != user["user_id"]:
        raise NotFoundError("Session not found")
    store.delete(session_id)
    logger.info("Session %s discarded by user", session_id)
    return FinalizeResponse(ok=True, closed=True)


@router.post("/{session_id}/reopen", response_model=FinalizeResponse)
async def reopen_session(
    session_id: str = _SESSION_ID,
    store: MongoSessionStore = Depends(get_store),
    user: dict[str, str] = Depends(require_user),
) -> FinalizeResponse:
    """Reopen a previously-finalized session so editing can resume.

    Reuses ``FinalizeResponse`` (same ``{ok, closed}`` shape) since the
    only state mutation is the ``closed`` flag flipping back to ``False``.
    Stage stays at ``STAGE_FINAL`` so the user lands in free-form revision
    mode rather than restarting the draft/approve workflow.
    """
    session = store.get(session_id)
    if session is None or session.get("user_id") != user["user_id"]:
        raise NotFoundError("Session not found")
    if not session.get("closed"):
        # Idempotent: reopening an already-open session is a no-op success.
        return FinalizeResponse(ok=True, closed=False)
    try:
        store.reopen(session_id)
    except KeyError:
        raise NotFoundError("Session not found") from None
    logger.info("Session %s reopened", session_id)
    return FinalizeResponse(ok=True, closed=False)


def _latest_assistant_message(messages: list[dict[str, str]]) -> str | None:
    """Return the most recent assistant message content, if any."""
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("content", "").strip():
            return message["content"]
    return None


def _pdf_filename(job_title: str) -> str:
    """Build a safe download filename from the job title."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", job_title).strip("_") or "proposal"
    return f"{slug[:60]}_proposal.pdf"


def _display_user_content(content: str) -> str:
    """Strip hidden control directives before returning chat history."""
    cleaned = re.sub(
        r"\n\n\[Instruction to assistant:.*\]\s*$",
        "",
        content,
        flags=re.DOTALL,
    ).strip()
    return cleaned


def _to_display_messages(messages: list[dict[str, str]]) -> list[SessionMessage]:
    out: list[SessionMessage] = []
    for message in messages:
        role = str(message.get("role", ""))
        if role == "system":
            continue
        content = str(message.get("content", ""))
        if role == "user":
            content = _display_user_content(content)
            if not content:
                continue
        if not content.strip():
            continue
        out.append(SessionMessage(role=role, content=content))
    return out


@router.get("/list", response_model=SessionListResponse)
async def list_sessions(
    store: MongoSessionStore = Depends(get_store),
    user: dict[str, str] = Depends(require_user),
) -> SessionListResponse:
    """List the authenticated user's previous sessions."""
    return SessionListResponse(sessions=store.list_for_user(user["user_id"]))


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str = _SESSION_ID,
    store: MongoSessionStore = Depends(get_store),
    user: dict[str, str] = Depends(require_user),
) -> SessionDetailResponse:
    """Load one session so the frontend can switch between histories."""
    session = store.get(session_id)
    if session is None or session.get("user_id") != user["user_id"]:
        raise NotFoundError("Session not found")
    intake = session.get("intake", {})
    intake_map = {str(k): str(v) for k, v in intake.items()}
    return SessionDetailResponse(
        session_id=session_id,
        stage=str(session.get("stage", STAGE_QUESTIONING)),
        closed=bool(session.get("closed", False)),
        job_title=intake_map.get("job_title", "Untitled JD"),
        intake=intake_map,
        messages=_to_display_messages(session.get("messages", [])),
    )


@router.get("/{session_id}/proposal.pdf")
async def download_proposal_pdf(
    session_id: str = _SESSION_ID,
    template: str | None = Query(
        None,
        description="Override the user's default PDF template for this export only.",
        max_length=64,
    ),
    store: MongoSessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings_dep),
    llm: LlmClient = Depends(get_llm),
    user: dict[str, str] = Depends(require_user),
) -> Response:
    """Export the finalized proposal of a session as a templated PDF."""
    session = store.get(session_id)
    if session is None:
        raise NotFoundError("Session not found")
    if session.get("user_id") != user["user_id"]:
        raise NotFoundError("Session not found")
    if session.get("stage") != STAGE_FINAL:
        raise AppError(
            "Proposal is not finalized yet. Approve the draft first.",
            status_code=409,
        )

    proposal_text = _latest_assistant_message(session["messages"])
    if not proposal_text:
        raise AppError("No proposal content found for this session.", status_code=409)

    intake = session.get("intake", {})
    raw_title = str(intake.get("job_title", ""))
    # Cover title: prefer a cached LLM-derived title if we've already paid
    # the cost on a prior export. Otherwise derive once, cache, reuse.
    # The original ``job_title`` stays in the intake (used for filenames,
    # history listings, etc.) so this only affects the PDF cover.
    cached_pdf_title = str(session.get("pdf_title", "")).strip()
    if cached_pdf_title:
        job_title = cached_pdf_title
    else:
        job_title = await _derive_pdf_title(
            llm,
            job_title=raw_title,
            job_description=str(intake.get("job_description", "")),
        )
        if job_title and job_title != raw_title:
            try:
                store.set_field(session_id, "pdf_title", job_title)
            except KeyError:
                # Session was evicted mid-request; render with the derived
                # title anyway, just don't persist it.
                pass
    profile = await run_in_threadpool(
        profile_store.get_profile, settings, user["user_id"]
    )
    logo_payload = await run_in_threadpool(
        profile_store.load_logo_bytes, settings, user["user_id"]
    )
    logo_bytes = logo_payload[0] if logo_payload else None
    logo_suffix = logo_payload[2] if logo_payload else ""

    company_name = profile.get("company_name") or settings.pdf_brand_name
    # Per-request override wins; otherwise honour the user's saved default.
    template_id = template or profile.get("template_id") or ""
    # Only print the company intro on the PDF cover when the user explicitly
    # opted in via the "Use intro verbatim" toggle. Otherwise the AI-generated
    # "About Us" subsection inside the proposal body carries the narration.
    cover_intro = (
        profile.get("company_intro", "")
        if profile.get("intro_verbatim")
        else ""
    )
    pdf_bytes = await run_in_threadpool(
        render_proposal_pdf,
        proposal_text=proposal_text,
        job_title=job_title,
        client_name=str(intake.get("client_name", "")),
        brand_name=company_name,
        company_intro=cover_intro,
        signature=profile.get("signature", ""),
        accent_color=profile.get("accent_color", ""),
        logo_bytes=logo_bytes,
        logo_suffix=logo_suffix,
        template_id=template_id,
    )
    logger.info("Exported proposal PDF for session %s (%d bytes)", session_id, len(pdf_bytes))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_pdf_filename(job_title)}"'
        },
    )
