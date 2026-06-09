"""Per-user company profile endpoints.

The profile data branded onto generated proposals lives here. Text fields go
through JSON; the logo is a separate multipart upload so binary stays out of
the JSON payloads. Every endpoint scopes to the authenticated user.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Response, UploadFile

from .. import profiles as profile_store
from ..auth import require_user
from ..config import Settings
from ..errors import AppError, NotFoundError
from ..schemas import ProfileResponse, ProfileUpdateRequest
from ..services import get_settings_dep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile", tags=["profile"])

_LOGO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _to_response(profile: dict) -> ProfileResponse:
    return ProfileResponse(**{k: profile.get(k, "") for k in ProfileResponse.model_fields})


@router.get("", response_model=ProfileResponse)
def get_profile(
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> ProfileResponse:
    """Return the authenticated user's company profile."""
    return _to_response(profile_store.get_profile(settings, user["user_id"]))


@router.put("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> ProfileResponse:
    """Update text fields on the user's company profile."""
    try:
        profile = profile_store.update_profile(
            settings,
            user["user_id"],
            company_name=payload.company_name,
            company_intro=payload.company_intro,
            intro_verbatim=payload.intro_verbatim,
            signature=payload.signature,
            accent_color=payload.accent_color,
            template_id=payload.template_id,
        )
    except ValueError as exc:
        raise AppError(str(exc), status_code=400) from exc
    logger.info("Profile updated for user %s", user["user_id"])
    return _to_response(profile)


@router.post("/logo", response_model=ProfileResponse)
async def upload_logo(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> ProfileResponse:
    """Upload (or replace) the user's company logo."""
    original = file.filename or "logo.png"
    suffix = Path(original).suffix.lower()
    if suffix not in _LOGO_SUFFIXES:
        allowed = ", ".join(sorted(_LOGO_SUFFIXES))
        raise AppError(
            f"Unsupported image type '{suffix or '(none)'}'. Allowed: {allowed}",
            status_code=400,
        )

    payload = await file.read()
    await file.close()
    if not payload:
        raise AppError("Uploaded file is empty.", status_code=400)
    if len(payload) > settings.profile_logo_max_bytes:
        limit_mb = settings.profile_logo_max_bytes // (1024 * 1024)
        raise AppError(
            f"Logo too large (limit {limit_mb} MB).", status_code=413
        )

    mime = file.content_type or _suffix_to_mime(suffix)
    try:
        profile = profile_store.save_logo(
            settings,
            user["user_id"],
            payload=payload,
            suffix=suffix,
            mime=mime,
        )
    except ValueError as exc:
        raise AppError(str(exc), status_code=400) from exc

    logger.info(
        "Logo saved for user %s (%d bytes, %s)",
        user["user_id"],
        len(payload),
        mime,
    )
    return _to_response(profile)


@router.delete("/logo", response_model=ProfileResponse)
def delete_logo(
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> ProfileResponse:
    """Remove the user's logo file and clear its metadata."""
    profile = profile_store.delete_logo(settings, user["user_id"])
    return _to_response(profile)


@router.get("/logo")
def serve_logo(
    settings: Settings = Depends(get_settings_dep),
    user: dict[str, str] = Depends(require_user),
) -> Response:
    """Stream the user's logo bytes back with the original mime type."""
    result = profile_store.load_logo_bytes(settings, user["user_id"])
    if result is None:
        raise NotFoundError("No logo uploaded.")
    payload, mime, _suffix = result
    return Response(
        content=payload,
        media_type=mime,
        headers={"Cache-Control": "private, max-age=0, must-revalidate"},
    )


def _suffix_to_mime(suffix: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "application/octet-stream")
