"""Facade over the template registry.

Historically this module rendered a single hard-coded layout. Layouts now
live in :mod:`app.pdf_templates`; this module keeps the public entry point
stable so callers do not need to know which template implementation runs.
"""

from __future__ import annotations

from .pdf_templates import DEFAULT_TEMPLATE_ID, get_template, list_templates
from .pdf_templates._shared import DEFAULT_ACCENT, parse_proposal

__all__ = [
    "DEFAULT_ACCENT",
    "DEFAULT_TEMPLATE_ID",
    "list_templates",
    "parse_proposal",
    "render_proposal_pdf",
]


def render_proposal_pdf(
    *,
    proposal_text: str,
    job_title: str = "",
    client_name: str = "",
    brand_name: str = "",
    company_intro: str = "",
    signature: str = "",
    accent_color: str = "",
    logo_bytes: bytes | None = None,
    logo_suffix: str = "",
    template_id: str | None = None,
) -> bytes:
    """Render the proposal using the named template (or the default)."""
    template = get_template(template_id)
    return template.render(
        proposal_text=proposal_text,
        job_title=job_title,
        client_name=client_name,
        brand_name=brand_name,
        company_intro=company_intro,
        signature=signature,
        accent_color=accent_color,
        logo_bytes=logo_bytes,
        logo_suffix=logo_suffix,
    )
