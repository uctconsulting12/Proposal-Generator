"""Per-user company profile storage.

A profile holds the bits used to brand a freelancer's proposals: company
name, a short "about us" introduction (also used as LLM context so the
assistant writes in the user's voice), an optional signature, an accent
colour for the PDF, and an optional logo image. Text fields live in
MongoDB next to the user; the logo is stored on disk under
``profiles/<user_id>/logo.<ext>`` so MongoDB stays small and the file can
be streamed directly.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
from pymongo import MongoClient

from .config import Settings

_ALLOWED_LOGO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

EMPTY_PROFILE = {
    "company_name": "",
    "company_intro": "",
    # When False (default) the AI condenses the intro into a short 1-2
    # sentence About Us paragraph and the PDF cover hides the intro block.
    # When True the full intro is used verbatim everywhere.
    "intro_verbatim": False,
    "signature": "",
    "accent_color": "#0f766e",
    "template_id": "modern",
    "has_logo": False,
    "logo_mime": "",
    "logo_updated_at": "",
    "updated_at": "",
}


def _users(settings: Settings):
    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    return db["users"]


def _user_id_to_object(user_id: str) -> ObjectId:
    return ObjectId(user_id)


def _user_logo_dir(settings: Settings, user_id: str) -> Path:
    directory = settings.profiles_dir / user_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_profile(settings: Settings, user_id: str) -> dict[str, Any]:
    """Return the profile for a user, falling back to empty defaults."""
    doc = _users(settings).find_one(
        {"_id": _user_id_to_object(user_id)}, {"profile": 1}
    )
    profile = (doc or {}).get("profile") or {}
    merged = {**EMPTY_PROFILE, **profile}
    # Reflect on-disk truth for the logo, in case it was deleted out-of-band.
    merged["has_logo"] = bool(merged.get("logo_mime")) and _find_logo_file(
        settings, user_id
    ) is not None
    return merged


def update_profile(
    settings: Settings,
    user_id: str,
    *,
    company_name: str | None = None,
    company_intro: str | None = None,
    intro_verbatim: bool | None = None,
    signature: str | None = None,
    accent_color: str | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    """Update text fields on a profile (any None argument is left untouched)."""
    # Local import to avoid a circular dependency at module load.
    from .pdf_templates import get_template

    update: dict[str, Any] = {"profile.updated_at": _now_iso()}
    if company_name is not None:
        update["profile.company_name"] = company_name.strip()
    if company_intro is not None:
        update["profile.company_intro"] = company_intro.strip()
    if intro_verbatim is not None:
        update["profile.intro_verbatim"] = bool(intro_verbatim)
    if signature is not None:
        update["profile.signature"] = signature.strip()
    if accent_color is not None:
        color = accent_color.strip()
        if not _HEX_COLOR_RE.match(color):
            raise ValueError("accent_color must be a #RRGGBB hex string.")
        update["profile.accent_color"] = color.lower()
    if template_id is not None:
        chosen = template_id.strip().lower()
        # get_template falls back silently — reject explicitly here so the
        # API surface stays honest about what's valid.
        if get_template(chosen).id != chosen:
            raise ValueError(f"Unknown template id '{template_id}'.")
        update["profile.template_id"] = chosen

    _users(settings).update_one(
        {"_id": _user_id_to_object(user_id)}, {"$set": update}, upsert=False
    )
    return get_profile(settings, user_id)


def save_logo(
    settings: Settings, user_id: str, *, payload: bytes, suffix: str, mime: str
) -> dict[str, Any]:
    """Persist a new logo on disk and update profile metadata in MongoDB."""
    suffix = suffix.lower()
    if suffix not in _ALLOWED_LOGO_SUFFIXES:
        allowed = ", ".join(sorted(_ALLOWED_LOGO_SUFFIXES))
        raise ValueError(f"Unsupported image type '{suffix}'. Allowed: {allowed}")

    directory = _user_logo_dir(settings, user_id)
    # Wipe any previous logo (extension may differ) so listing stays clean.
    for existing in directory.glob("logo.*"):
        try:
            existing.unlink()
        except OSError:
            pass
    target = directory / f"logo{suffix}"
    target.write_bytes(payload)

    _users(settings).update_one(
        {"_id": _user_id_to_object(user_id)},
        {
            "$set": {
                "profile.logo_mime": mime,
                "profile.logo_updated_at": _now_iso(),
                "profile.updated_at": _now_iso(),
            }
        },
    )
    return get_profile(settings, user_id)


def delete_logo(settings: Settings, user_id: str) -> dict[str, Any]:
    """Remove the logo file and clear its metadata."""
    directory = settings.profiles_dir / user_id
    if directory.exists():
        for existing in directory.glob("logo.*"):
            try:
                existing.unlink()
            except OSError:
                pass
    _users(settings).update_one(
        {"_id": _user_id_to_object(user_id)},
        {
            "$set": {
                "profile.logo_mime": "",
                "profile.logo_updated_at": "",
                "profile.updated_at": _now_iso(),
            }
        },
    )
    return get_profile(settings, user_id)


def load_logo_bytes(
    settings: Settings, user_id: str
) -> tuple[bytes, str, Path] | None:
    """Return (bytes, mime, path) of the user's logo, or None if absent."""
    path = _find_logo_file(settings, user_id)
    if path is None:
        return None
    profile = get_profile(settings, user_id)
    mime = profile.get("logo_mime") or _mime_for(path.suffix)
    return path.read_bytes(), mime, path


def _find_logo_file(settings: Settings, user_id: str) -> Path | None:
    directory = settings.profiles_dir / user_id
    if not directory.exists():
        return None
    for candidate in directory.glob("logo.*"):
        if candidate.is_file() and candidate.suffix.lower() in _ALLOWED_LOGO_SUFFIXES:
            return candidate
    return None


def _mime_for(suffix: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix.lower(), "application/octet-stream")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
