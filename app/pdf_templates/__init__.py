"""PDF template registry.

A *template* knows how to lay out a finalised proposal — cover, headings,
body type, footer — given the same set of inputs (proposal text, profile
data, accent colour, logo). All templates share the parsing logic from
``app.pdf`` so the proposal markup written by the LLM renders identically
across them; only the visual styling differs.

Add a new style by writing a render function and registering it below.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .modern import render as _render_modern
from .classic import render as _render_classic
from .bold import render as _render_bold
from .technical import render as _render_technical

# Renderer signature: every template takes the same keyword arguments so the
# session route doesn't have to branch on the chosen style.
Renderer = Callable[..., bytes]


@dataclass(frozen=True)
class TemplateInfo:
    """User-visible metadata + the renderer callable for one template."""

    id: str
    name: str
    description: str
    tagline: str
    render: Renderer


_TEMPLATES: dict[str, TemplateInfo] = {
    "modern": TemplateInfo(
        id="modern",
        name="Modern Teal",
        description=(
            "Bold accent band across the cover, sans-serif body, accent-coloured "
            "headings. The default — works for SaaS, agencies, and tech proposals."
        ),
        tagline="The crowd-pleaser",
        render=_render_modern,
    ),
    "classic": TemplateInfo(
        id="classic",
        name="Classic Serif",
        description=(
            "Conservative serif typeface, minimal colour, generous whitespace. "
            "Picks up gravitas — ideal for enterprise, legal, or government bids."
        ),
        tagline="Conservative & timeless",
        render=_render_classic,
    ),
    "bold": TemplateInfo(
        id="bold",
        name="Bold Statement",
        description=(
            "Full-bleed accent cover with reversed white text, oversized title, "
            "section numbers. Use when you want the proposal to feel like a pitch deck."
        ),
        tagline="Pitch-deck energy",
        render=_render_bold,
    ),
    "technical": TemplateInfo(
        id="technical",
        name="Technical Brief",
        description=(
            "Numbered sections with subsections (1, 1.1, 1.2), navy table headers, "
            "centred logo cover and a clean footer. Use for RFP responses, technical "
            "architecture docs, and consultative pitches that need to look formal."
        ),
        tagline="RFP / consulting style",
        render=_render_technical,
    ),
}

DEFAULT_TEMPLATE_ID = "modern"


def list_templates() -> list[TemplateInfo]:
    """All registered templates in display order."""
    return list(_TEMPLATES.values())


def get_template(template_id: str | None) -> TemplateInfo:
    """Resolve a template id, falling back to the default if unknown/missing."""
    if template_id and template_id in _TEMPLATES:
        return _TEMPLATES[template_id]
    return _TEMPLATES[DEFAULT_TEMPLATE_ID]


__all__ = [
    "DEFAULT_TEMPLATE_ID",
    "TemplateInfo",
    "get_template",
    "list_templates",
]

# Quiet "imported but unused" — Path is exposed for type-hint convenience
# in template renderers that import from this package.
_ = Path
