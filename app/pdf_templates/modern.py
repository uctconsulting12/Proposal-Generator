"""Modern Teal template — the default style.

Accent band across the top of the cover, sans-serif body, accent-coloured
headings and a thin accent rule above the footer. This is a near-exact
preservation of the previous renderer in ``app.pdf`` so existing exports
continue to look the same when no template is explicitly chosen.
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


class _ModernPDF(FPDF):
    def __init__(self, *, brand: str, running_title: str, accent: tuple[int, int, int]) -> None:
        super().__init__(format="A4")
        self._brand = brand
        self._running_title = running_title
        self._accent = accent
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(True, margin=22)

    def header(self) -> None:  # noqa: D102
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(130)
        self.cell(0, 6, self._running_title[:70])
        if self._brand:
            self.cell(0, 6, self._brand, align="R")
        self.ln(8)
        self.set_text_color(0)

    def footer(self) -> None:  # noqa: D102
        self.set_y(-15)
        self.set_draw_color(*self._accent)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(140)
        if self._brand:
            self.cell(0, 6, self._brand, align="L")
        self.cell(0, 6, f"Page {self.page_no()}", align="R")
        self.set_text_color(0)


def _cover(
    pdf: _ModernPDF,
    *,
    job_title: str,
    client: str,
    brand: str,
    intro: str,
    accent: tuple[int, int, int],
    logo: Path | None,
) -> None:
    pdf.set_fill_color(*accent)
    pdf.set_text_color(255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 11, "  PROJECT PROPOSAL", fill=True)
    pdf.ln(16)

    cursor_y = pdf.get_y()
    if logo is not None and logo.exists():
        try:
            pdf.image(str(logo), x=pdf.l_margin, y=cursor_y, h=22)
        except Exception:
            pass
        pdf.set_xy(pdf.l_margin + 32, cursor_y)
    else:
        pdf.set_xy(pdf.l_margin, cursor_y)

    pdf.set_text_color(20)
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 9, job_title or "Proposal")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90)
    for label, value in (
        ("Prepared for", client),
        ("Prepared by", brand),
        ("Date", date.today().strftime("%B %d, %Y")),
    ):
        if value:
            pdf.cell(0, 6, f"{label}: {value}")
            pdf.ln(6)

    if intro:
        pdf.ln(3)
        pdf.set_text_color(40)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "About Us")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(70)
        pdf.multi_cell(0, 5.4, intro)

    pdf.ln(4)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.6)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)
    pdf.set_text_color(0)


def _table(pdf, payload, accent) -> None:
    header = payload.get("header") or []
    rows = payload.get("rows") or []
    if not header:
        return
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9.5)
    heading_style = FontFace(
        emphasis="BOLD", color=255, fill_color=accent, size_pt=9.5
    )
    # Cells that are a single ``[text](url)`` markdown link render with the
    # accent colour + underline so the reader sees them as obvious hyperlinks
    # (e.g. the GitHub repo cell in the Section 3 portfolio table).
    link_cell_style = FontFace(emphasis="UNDERLINE", color=accent)
    with pdf.table(
        text_align="LEFT",
        line_height=5.2,
        headings_style=heading_style,
        cell_fill_color=(245, 248, 250),
        cell_fill_mode=TableCellFillMode.ROWS,
        borders_layout="MINIMAL",
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
    pdf.ln(2)


def _body(pdf: _ModernPDF, elements, accent) -> None:
    for kind, content in elements:
        pdf.set_x(pdf.l_margin)
        if kind == "space":
            pdf.ln(2.5)
        elif kind == "heading":
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*accent)
            pdf.multi_cell(0, 7, content)
            pdf.set_text_color(0)
            pdf.ln(1)
        elif kind == "subheading":
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*accent)
            pdf.multi_cell(0, 6, content)
            pdf.set_text_color(0)
        elif kind == "bullet":
            pdf.set_font("Helvetica", "", 10.5)
            saved = pdf.l_margin
            pdf.set_left_margin(saved + 6)
            pdf.set_x(saved + 6)
            write_inline_runs(pdf, f"- {content}", 5.6, accent)
            pdf.set_left_margin(saved)
            pdf.set_x(saved)
        elif kind == "table":
            _table(pdf, content, accent)
        else:
            pdf.set_font("Helvetica", "", 10.5)
            write_inline_runs(pdf, content, 5.6, accent)
            pdf.ln(1.5)


def _signature(pdf: _ModernPDF, signature: str, accent) -> None:
    pdf.ln(6)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + 60, y)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60)
    pdf.multi_cell(0, 5.4, signature)
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
    job = sanitize(job_title)
    client = sanitize(client_name)
    brand = sanitize(brand_name)
    intro = sanitize(company_intro) if company_intro else ""
    signature_safe = sanitize(signature) if signature else ""
    accent = hex_to_rgb(accent_color)

    with LogoFile(logo_bytes, logo_suffix) as logo_handle:
        pdf = _ModernPDF(brand=brand, running_title=job, accent=accent)
        pdf.add_page()
        _cover(
            pdf,
            job_title=job,
            client=client,
            brand=brand,
            intro=intro,
            accent=accent,
            logo=logo_handle.path,
        )
        _body(pdf, parse_proposal(proposal_text), accent)
        if signature_safe:
            _signature(pdf, signature_safe, accent)
        return bytes(pdf.output())
