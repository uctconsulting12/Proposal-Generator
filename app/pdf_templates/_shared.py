"""Shared helpers used by every PDF template.

Centralises the bits that are *not* style choices — text sanitisation,
proposal parsing (headings, sub-headings, bullets, paragraphs, tables),
hex-to-RGB conversion, and a small helper for stashing a logo blob in a
temp file. Templates compose these utilities to keep their own render
functions short and focused on visual layout.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_ACCENT = (15, 118, 110)

_HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")

_UNICODE_REPLACEMENTS = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "•": "-", "…": "...",
    " ": " ", "™": "(TM)", "→": "->", "®": "(R)",
    "✅": "", "✨": "", "≥": ">=", "≤": "<=",
}

_SECTION_NAMES = {
    "introduction", "executive summary", "understanding of the project",
    "understanding", "understanding of requirements",
    "relevant past experience", "past experience",
    "our proven systems", "our proven systems - direct portfolio match",
    "proposed approach and scope", "proposed approach", "approach", "scope",
    "scope of work", "timeline and milestones", "timeline", "milestones",
    "proposed technical architecture", "technical architecture",
    "data and access requirements", "data & access requirements",
    "pricing", "cost", "budget", "assumptions", "why me", "why us",
    "about me", "about us", "conclusion", "next steps", "deliverables",
}

_BULLET_RE = re.compile(r"^\s*([-*•]|\d+[.)])\s+(.*)$")
_HEADING_MD_RE = re.compile(r"^\s*(#{1,6})\s+(.*)$")
_SUBSECTION_NUMBER_RE = re.compile(r"^\d+\.\d+(\.\d+)?\s+\S")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")
# Inline markdown link: [display text](https://...). Used to turn portfolio
# rows like "[queue_model](https://github.com/...)" into a clickable cell
# rather than leaking raw markdown syntax into the PDF.
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def sanitize(text: str) -> str:
    """Make text safe for Latin-1 core PDF fonts."""
    for src, dst in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


def clean_inline(text: str) -> str:
    """Strip markdown emphasis + backticks and sanitize.

    Use this for headings, subheadings, and *non-emphasis-rendering* table
    cells. For body bullets and paragraphs use ``preserve_inline`` instead so
    ``**bold**`` / ``*emphasis*`` runs survive into the renderer where they
    become real PDF font emphasis.
    """
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?<![\*\w])\*([^*]+)\*(?![\*\w])", r"\1", text)
    return sanitize(text.strip())


def preserve_inline(text: str) -> str:
    """Sanitize body text *without* destroying ``**bold**`` / ``*x*`` markers."""
    return sanitize(text.strip().replace("`", ""))


def split_link_cell(text: str) -> tuple[str, str | None]:
    """Decide how to render a table cell that may contain a markdown link.

    Three cases:
      * The whole cell is exactly one ``[display](url)`` → returns
        ``(display, url)`` so the caller can render the cell with a
        clickable annotation.
      * The cell contains a link mixed with extra text → the link syntax
        is collapsed to ``"display (url)"`` so the URL is still visible
        and copyable even though the cell can't be a single hyperlink.
      * No link present → returns ``(text, None)`` unchanged.
    """
    if not text:
        return ("", None)
    stripped = text.strip()
    match = _MD_LINK_RE.fullmatch(stripped)
    if match:
        return (sanitize(match.group(1).strip()), match.group(2).strip())
    if _MD_LINK_RE.search(stripped):
        flattened = _MD_LINK_RE.sub(
            lambda m: f"{m.group(1).strip()} ({m.group(2).strip()})", stripped
        )
        return (sanitize(flattened), None)
    return (sanitize(stripped), None)


def iter_link_segments(text: str) -> list[tuple[str, str | None]]:
    """Split ``text`` into ``(segment, url_or_None)`` pairs in document order.

    Kept for callers that only care about links. New callers should prefer
    :func:`iter_inline_runs`, which also surfaces bold runs.
    """
    if not text:
        return []
    parts: list[tuple[str, str | None]] = []
    cursor = 0
    for match in _MD_LINK_RE.finditer(text):
        if match.start() > cursor:
            parts.append((sanitize(text[cursor:match.start()]), None))
        parts.append((sanitize(match.group(1).strip()), match.group(2).strip()))
        cursor = match.end()
    if cursor < len(text):
        parts.append((sanitize(text[cursor:]), None))
    return parts or [(sanitize(text), None)]


# One regex that recognises all inline markup we care about in document
# order: markdown links, **bold** spans, and *emphasis* spans. Single-star
# emphasis is matched only when surrounded by non-word/non-star characters
# so an isolated asterisk in "5*4" doesn't accidentally start a run.
_INLINE_TOKEN_RE = re.compile(
    r"\[([^\]]+)\]\(([^)]+)\)"           # group 1=display, group 2=url
    r"|\*\*([^*]+)\*\*"                  # group 3 = **bold**
    r"|(?<![\*\w])\*([^*]+)\*(?![\*\w])" # group 4 = *emphasis*
)


def iter_inline_runs(text: str) -> list[tuple[str, str | None, bool]]:
    """Tokenize ``text`` into ``(segment, url_or_None, bold)`` triples.

    The renderer walks these in order, applying the right font style and/or
    link annotation per run. ``*emphasis*`` is intentionally treated as bold
    too — proposal subsection labels like ``*Why this matters:*`` deserve
    visual weight, not italic, in a client-facing PDF.
    """
    if not text:
        return []
    runs: list[tuple[str, str | None, bool]] = []
    cursor = 0
    for match in _INLINE_TOKEN_RE.finditer(text):
        if match.start() > cursor:
            runs.append((sanitize(text[cursor:match.start()]), None, False))
        if match.group(1) is not None:
            runs.append((sanitize(match.group(1).strip()), match.group(2).strip(), False))
        elif match.group(3) is not None:
            runs.append((sanitize(match.group(3)), None, True))
        elif match.group(4) is not None:
            runs.append((sanitize(match.group(4)), None, True))
        cursor = match.end()
    if cursor < len(text):
        runs.append((sanitize(text[cursor:]), None, False))
    return runs or [(sanitize(text), None, False)]


def write_inline_runs(pdf, text: str, line_height: float, accent) -> None:
    """Render ``text`` flowing inline, honouring bold + markdown links.

    Bold runs are emitted with ``set_font(style="B")``. Link runs are
    underlined in the accent colour and emitted with ``pdf.write(..., link=url)``
    so the PDF carries a real clickable annotation. A plain run falls
    through to a fast ``multi_cell`` path so most text still wraps cleanly.
    """
    runs = iter_inline_runs(text)
    if len(runs) == 1 and runs[0][1] is None and not runs[0][2]:
        pdf.multi_cell(0, line_height, runs[0][0])
        return
    for segment, url, bold in runs:
        if url and bold:
            pdf.set_text_color(*accent)
            pdf.set_font(style="BU")
            pdf.write(line_height, segment, link=url)
            pdf.set_font(style="")
            pdf.set_text_color(0)
        elif url:
            pdf.set_text_color(*accent)
            pdf.set_font(style="U")
            pdf.write(line_height, segment, link=url)
            pdf.set_font(style="")
            pdf.set_text_color(0)
        elif bold:
            pdf.set_font(style="B")
            pdf.write(line_height, segment)
            pdf.set_font(style="")
        else:
            pdf.write(line_height, segment)
    pdf.ln(line_height)


def _detect_heading_level(line: str) -> tuple[int, str] | None:
    """Return (level, text) for a heading line, or None.

    Level 1 = top section (e.g. "1. Executive Summary"). Level 2 = subsection
    (e.g. "2.1 Detection & Tracking"). The level lets templates style the
    hierarchy without re-deriving it.
    """
    stripped = line.strip()
    md = _HEADING_MD_RE.match(stripped)
    if md:
        hashes, content = md.group(1), md.group(2)
        level = 2 if len(hashes) >= 3 else 1
        return level, content.strip().strip("*").strip()
    if stripped.startswith("**") and stripped.endswith("**") and len(stripped) <= 80:
        bare = stripped.strip("*").strip()
        # "2.1 Foo" → subsection.
        if _SUBSECTION_NUMBER_RE.match(bare):
            return 2, bare
        return 1, bare
    normalised = re.sub(r"^[\d.)\s]+", "", stripped).strip().strip("*")
    normalised = normalised.rstrip(":").strip()
    if normalised.lower() in _SECTION_NAMES and len(stripped) <= 80:
        return 1, normalised
    if _SUBSECTION_NUMBER_RE.match(stripped) and len(stripped) <= 100:
        return 2, stripped
    return None


def _parse_table_row(line: str) -> list[str]:
    """Split a markdown table row ``|a|b|c|`` into trimmed cells."""
    inner = line.strip().strip("|")
    return [clean_inline(cell) for cell in inner.split("|")]


def parse_proposal(text: str) -> list[tuple[str, Any]]:
    """Parse proposal text into ``(kind, payload)`` elements.

    Kinds produced:
      ``space``       — blank line, no payload
      ``heading``     — payload is the heading text (top-level section)
      ``subheading``  — payload is the sub-section heading text
      ``bullet``      — payload is the bullet text
      ``para``        — payload is the paragraph text
      ``table``       — payload is ``{"header": [..], "rows": [[..], ..]}``
    """
    elements: list[tuple[str, Any]] = []
    lines = text.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]

        if not raw.strip():
            elements.append(("space", ""))
            i += 1
            continue

        # Markdown-style table: a line of pipes optionally followed by a
        # `|---|---|` separator, then more pipe-rows. We don't require the
        # separator (some LLMs forget it) — any block of consecutive pipe
        # lines counts as one table.
        if _TABLE_ROW_RE.match(raw):
            block = []
            while i < n and _TABLE_ROW_RE.match(lines[i]):
                block.append(lines[i])
                i += 1
            # Drop the optional separator row (---).
            rows = [
                _parse_table_row(line)
                for line in block
                if not _TABLE_SEPARATOR_RE.match(line.replace("|", "|"))
                or any(c not in " -:|" for c in line)
            ]
            rows = [r for r in rows if not all(set(cell) <= set("-:") for cell in r)]
            if rows:
                header, *body = rows
                elements.append(("table", {"header": header, "rows": body}))
            continue

        heading = _detect_heading_level(raw)
        if heading:
            level, content = heading
            kind = "heading" if level == 1 else "subheading"
            elements.append((kind, clean_inline(content)))
            i += 1
            continue

        bullet = _BULLET_RE.match(raw)
        if bullet:
            elements.append(("bullet", preserve_inline(bullet.group(2))))
            i += 1
            continue

        elements.append(("para", preserve_inline(raw.strip())))
        i += 1

    return elements


def hex_to_rgb(color: str | None) -> tuple[int, int, int]:
    """Parse a ``#RRGGBB`` hex value, falling back to ``DEFAULT_ACCENT``."""
    if not color:
        return DEFAULT_ACCENT
    match = _HEX_COLOR_RE.match(color.strip())
    if not match:
        return DEFAULT_ACCENT
    value = match.group(1)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def column_widths(pdf, total: int, weights: list[int] | None = None) -> list[float]:
    """Compute column widths that exactly span the printable area."""
    available = pdf.w - pdf.l_margin - pdf.r_margin
    if not weights or len(weights) != total:
        weights = [1] * total
    unit = available / sum(weights)
    return [w * unit for w in weights]


class LogoFile:
    """Context manager that spills logo bytes to a temp file fpdf can read."""

    def __init__(self, payload: bytes | None, suffix: str = "") -> None:
        self._payload = payload
        self._suffix = (suffix or ".png").lower()
        self.path: Path | None = None
        self._tmp = None

    def __enter__(self) -> "LogoFile":
        if self._payload:
            self._tmp = tempfile.NamedTemporaryFile(suffix=self._suffix, delete=False)
            self._tmp.write(self._payload)
            self._tmp.flush()
            self._tmp.close()
            self.path = Path(self._tmp.name)
        return self

    def __exit__(self, *_exc) -> None:
        if self.path is not None:
            try:
                self.path.unlink()
            except OSError:
                pass
