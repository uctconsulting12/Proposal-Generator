"""Technical template — modelled on the UCT proposal layout.

A formal numbered-section style with deep navy headings and a strong table
treatment. The cover is a centred logo + company block, bracketed by two
thick brand rules; body sections use ``N. Title`` (level 1) and ``N.M Title``
(level 2). Footer is a centred website / brand line on every page.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import TableCellFillMode
from fpdf.fonts import FontFace

from ._shared import (
    LogoFile,
    hex_to_rgb,
    parse_proposal,
    sanitize,
    split_link_cell,
    write_inline_runs,
)


# Phase / status colours used in the timeline cards.
_PHASE_COLORS = [
    (30, 144, 112),   # green
    (40, 96, 168),    # blue
    (200, 130, 30),   # amber
    (170, 70, 100),   # rose
]


class _TechnicalPDF(FPDF):
    """A4 document with no top header and a centred footer line."""

    def __init__(
        self,
        *,
        brand: str,
        footer_line: str,
        accent: tuple[int, int, int],
    ) -> None:
        super().__init__(format="A4")
        self._brand = brand
        self._footer_line = footer_line
        self._accent = accent
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(True, margin=22)
        self._section_counter = 0

    def header(self) -> None:  # noqa: D102
        # Intentionally empty — the cover handles page 1, body pages stay clean.
        return

    def footer(self) -> None:  # noqa: D102
        self.set_y(-14)
        self.set_font("Times", "B", 9)
        self.set_text_color(*self._accent)
        self.cell(0, 6, self._footer_line or self._brand, align="C")
        self.set_text_color(0)


def _cover(
    pdf: _TechnicalPDF,
    *,
    job_title: str,
    subtitle: str,
    brand: str,
    address: str,
    intro: str,
    accent: tuple[int, int, int],
    logo: Path | None,
) -> None:
    """Render the centred cover block: logo, brand, rules, title, optional intro."""
    pdf.ln(22)

    if logo is not None and logo.exists():
        try:
            # Centred logo, generous size.
            pdf.image(str(logo), x=(pdf.w - 38) / 2, y=pdf.get_y(), h=28)
            pdf.ln(34)
        except Exception:
            pdf.ln(6)
    else:
        pdf.ln(6)

    # Brand name, large and bold.
    pdf.set_font("Times", "B", 22)
    pdf.set_text_color(*accent)
    pdf.cell(0, 9, brand or "", align="C")
    pdf.ln(10)

    if address:
        pdf.set_font("Times", "", 10.5)
        pdf.set_text_color(120)
        pdf.cell(0, 5, address, align="C")
        pdf.ln(8)

    # First thick rule.
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.9)
    y = pdf.get_y() + 2
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(12)

    # Title block.
    pdf.set_font("Times", "B", 28)
    pdf.set_text_color(*accent)
    pdf.multi_cell(0, 12, job_title or "Proposal", align="C")
    pdf.ln(1)
    if subtitle:
        pdf.set_font("Times", "", 16)
        pdf.set_text_color(*accent)
        pdf.multi_cell(0, 8, subtitle, align="C")

    pdf.ln(8)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.9)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(20)

    # Prepared-for / by / date block stays compact.
    pdf.set_font("Times", "", 11)
    pdf.set_text_color(80)
    pdf.cell(0, 6, f"Date: {date.today().strftime('%B %d, %Y')}", align="C")
    pdf.ln(6)

    if intro:
        pdf.ln(8)
        pdf.set_font("Times", "I", 11)
        pdf.set_text_color(70)
        pdf.multi_cell(0, 6, intro, align="C")

    # Body always starts on page 2 so the cover stays clean.
    pdf.add_page()
    pdf.set_text_color(0)


def _heading(pdf: _TechnicalPDF, content: str, accent) -> None:
    """Top-level numbered section heading with a thin accent rule."""
    pdf.ln(3)
    # If content doesn't already start with a number, auto-number it.
    pdf._section_counter += 1
    label = content
    if not _starts_with_number(label):
        label = f"{pdf._section_counter}. {label}"
    pdf.set_font("Times", "B", 16)
    pdf.set_text_color(*accent)
    pdf.cell(0, 8, label)
    pdf.ln(8)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.5)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(4)
    pdf.set_text_color(0)


def _subheading(pdf: _TechnicalPDF, content: str, accent) -> None:
    pdf.ln(2)
    pdf.set_font("Times", "B", 12.5)
    pdf.set_text_color(*accent)
    pdf.multi_cell(0, 6.5, content)
    pdf.set_text_color(0)


def _bullet(pdf: _TechnicalPDF, content: str, accent) -> None:
    pdf.set_font("Times", "", 11)
    saved = pdf.l_margin
    pdf.set_left_margin(saved + 6)
    pdf.set_x(saved + 6)
    write_inline_runs(pdf, f"- {content}", 5.8, accent)
    pdf.set_left_margin(saved)
    pdf.set_x(saved)


def _para(pdf: _TechnicalPDF, content: str, accent) -> None:
    pdf.set_font("Times", "", 11)
    pdf.set_text_color(30)
    write_inline_runs(pdf, content, 5.8, accent)
    pdf.set_text_color(0)
    pdf.ln(1.2)


def _table(pdf, payload, accent) -> None:
    header = payload.get("header") or []
    rows = payload.get("rows") or []
    if not header:
        return
    pdf.ln(2)
    pdf.set_font("Times", "", 10.5)
    heading_style = FontFace(
        emphasis="BOLD", color=255, fill_color=accent, size_pt=10.5
    )
    link_cell_style = FontFace(emphasis="UNDERLINE", color=accent)
    with pdf.table(
        text_align="LEFT",
        line_height=5.6,
        headings_style=heading_style,
        cell_fill_color=(244, 248, 252),
        cell_fill_mode=TableCellFillMode.ROWS,
        borders_layout="SINGLE_TOP_LINE",
        width=pdf.w - pdf.l_margin - pdf.r_margin,
    ) as table:
        head = table.row()
        for cell in header:
            head.cell(cell)
        for body_row in rows:
            cells = list(body_row) + [""] * (len(header) - len(body_row))
            row = table.row()
            for cell in cells:
                display, url = split_link_cell(cell)
                if url:
                    row.cell(display, link=url, style=link_cell_style)
                else:
                    row.cell(display)
    pdf.ln(3)


def _starts_with_number(text: str) -> bool:
    head = text.split(maxsplit=1)[0] if text else ""
    return head and head[0].isdigit()


def _body(pdf: _TechnicalPDF, elements, accent) -> None:
    for kind, content in elements:
        # fpdf2's table() context leaves the cursor at the bottom-right of the
        # last cell, which makes the next multi_cell(0,...) report ~0 width.
        # Reset X to the left margin before every block to be safe.
        pdf.set_x(pdf.l_margin)
        if kind == "space":
            pdf.ln(2.2)
        elif kind == "heading":
            _heading(pdf, content, accent)
        elif kind == "subheading":
            _subheading(pdf, content, accent)
        elif kind == "bullet":
            _bullet(pdf, content, accent)
        elif kind == "table":
            _table(pdf, content, accent)
        else:
            _para(pdf, content, accent)


def _signature(pdf: _TechnicalPDF, signature: str, accent) -> None:
    pdf.ln(8)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + 60, y)
    pdf.ln(2)
    pdf.set_font("Times", "I", 10.5)
    pdf.set_text_color(70)
    pdf.multi_cell(0, 5.6, signature)
    pdf.set_text_color(0)


def render(
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
) -> bytes:
    # Split the title on the first " for " / " - " / ":" so the cover
    # gets a tight main title and an italic subtitle line below it.
    title, subtitle = _split_title(job_title)
    job_safe = sanitize(title)
    subtitle_safe = sanitize(subtitle)
    client_safe = sanitize(client_name)
    brand_safe = sanitize(brand_name)
    intro_safe = sanitize(company_intro) if company_intro else ""
    sig_safe = sanitize(signature) if signature else ""
    accent = hex_to_rgb(accent_color)

    # Footer carries the brand name on every page (the reference PDF used
    # a website URL — we use the brand so it works for any user).
    footer_line = brand_safe or client_safe

    with LogoFile(logo_bytes, logo_suffix) as logo_handle:
        pdf = _TechnicalPDF(
            brand=brand_safe, footer_line=footer_line, accent=accent
        )
        pdf.add_page()
        _cover(
            pdf,
            job_title=job_safe,
            subtitle=subtitle_safe,
            brand=brand_safe,
            address=client_safe and f"Prepared for {client_safe}" or "",
            intro=intro_safe,
            accent=accent,
            logo=logo_handle.path,
        )
        _body(pdf, parse_proposal(proposal_text), accent)
        if sig_safe:
            _signature(pdf, sig_safe, accent)
        return bytes(pdf.output())


def _split_title(title: str) -> tuple[str, str]:
    """Split a title into (main, subtitle).

    Splits on the first ``" for "`` / ``" - "`` / ``": "`` so something like
    ``"AI-Powered CCTV Monitoring System for Retail Store Intelligence"`` reads
    as a hero title + supporting line on the cover.
    """
    if not title:
        return "", ""
    for sep in (" for ", " - ", " — ", ": "):
        if sep in title:
            head, tail = title.split(sep, 1)
            return head.strip(), tail.strip()
    return title.strip(), ""


# Quiet "imported but unused" for stdlib helpers used elsewhere.
_ = _PHASE_COLORS
