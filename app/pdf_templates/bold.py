"""Bold Statement template.

Full-bleed accent cover (white text on a coloured block), oversized title,
numbered sections, beefy headings. Reads like a pitch deck cover.
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


class _BoldPDF(FPDF):
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
        # Small accent square + brand on the left, page indicator on the right.
        self.set_fill_color(*self._accent)
        self.rect(self.l_margin, 10, 4, 4, "F")
        self.set_xy(self.l_margin + 6, 9.5)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(40)
        self.cell(0, 5, self._brand or self._running_title[:60])
        self.set_xy(self.l_margin, 9.5)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(140)
        self.cell(0, 5, f"{self.page_no():02d}", align="R")
        self.ln(8)
        self.set_text_color(0)

    def footer(self) -> None:  # noqa: D102
        self.set_y(-14)
        self.set_fill_color(*self._accent)
        self.rect(self.l_margin, self.get_y(), 3, 3, "F")
        self.set_xy(self.l_margin + 5, self.get_y() - 0.5)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(60)
        if self._brand:
            self.cell(0, 5, self._brand.upper())
        self.set_text_color(140)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, f"Page {self.page_no()}", align="R")
        self.set_text_color(0)


def _cover(
    pdf: _BoldPDF,
    *,
    job_title: str,
    client: str,
    brand: str,
    intro: str,
    accent: tuple[int, int, int],
    logo: Path | None,
) -> None:
    # Full-bleed accent block across the top half of the cover.
    block_h = 110
    pdf.set_fill_color(*accent)
    pdf.rect(0, 0, pdf.w, block_h, "F")

    # Optional logo, white-backgrounded so transparent logos read.
    if logo is not None and logo.exists():
        try:
            pdf.image(str(logo), x=pdf.l_margin, y=18, h=22)
        except Exception:
            pass

    pdf.set_xy(pdf.l_margin, 50)
    pdf.set_text_color(255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, "PROJECT PROPOSAL")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 30)
    pdf.multi_cell(0, 12, job_title or "Proposal")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    if client:
        pdf.cell(0, 6, f"For {client}")
        pdf.ln(6)

    # Below the block: prepared-by + intro on a neutral background.
    pdf.set_y(block_h + 12)
    pdf.set_text_color(60)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "PREPARED BY")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(20)
    pdf.cell(0, 7, brand or "")
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(110)
    pdf.cell(0, 5, date.today().strftime("%B %d, %Y"))
    pdf.ln(8)

    if intro:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(60)
        pdf.cell(0, 5, "ABOUT US")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(70)
        pdf.multi_cell(0, 5.4, intro)

    pdf.ln(6)
    pdf.set_text_color(0)
    # Force a page break for the body so the cover stays clean.
    pdf.add_page()


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
    link_cell_style = FontFace(emphasis="UNDERLINE", color=accent)
    with pdf.table(
        text_align="LEFT",
        line_height=5.4,
        headings_style=heading_style,
        cell_fill_color=(250, 250, 250),
        cell_fill_mode=TableCellFillMode.ROWS,
        borders_layout="NO_HORIZONTAL_LINES",
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


def _body(pdf: _BoldPDF, elements, accent) -> None:
    section_number = 0
    for kind, content in elements:
        pdf.set_x(pdf.l_margin)
        if kind == "space":
            pdf.ln(2.5)
        elif kind == "heading":
            section_number += 1
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*accent)
            pdf.cell(0, 5, f"SECTION {section_number:02d}")
            pdf.ln(6)
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(20)
            pdf.multi_cell(0, 8, content)
            pdf.set_text_color(0)
            pdf.ln(2)
        elif kind == "subheading":
            pdf.ln(1.5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*accent)
            pdf.multi_cell(0, 6, content)
            pdf.set_text_color(0)
        elif kind == "table":
            _table(pdf, content, accent)
        elif kind == "bullet":
            pdf.set_font("Helvetica", "", 10.5)
            saved = pdf.l_margin
            # Bullet uses a small accent dash.
            pdf.set_text_color(*accent)
            pdf.cell(4, 5.6, "-")
            pdf.set_text_color(40)
            pdf.set_left_margin(saved + 6)
            pdf.set_x(saved + 6)
            write_inline_runs(pdf, content, 5.6, accent)
            pdf.set_left_margin(saved)
            pdf.set_x(saved)
            pdf.set_text_color(0)
        else:
            pdf.set_font("Helvetica", "", 10.5)
            pdf.set_text_color(45)
            write_inline_runs(pdf, content, 5.8, accent)
            pdf.set_text_color(0)
            pdf.ln(1.5)


def _signature(pdf: _BoldPDF, signature: str, accent) -> None:
    pdf.ln(8)
    pdf.set_fill_color(*accent)
    pdf.rect(pdf.l_margin, pdf.get_y(), 5, 5, "F")
    pdf.set_xy(pdf.l_margin + 8, pdf.get_y() - 0.5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(40)
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
    sig = sanitize(signature) if signature else ""
    accent = hex_to_rgb(accent_color)

    with LogoFile(logo_bytes, logo_suffix) as logo_handle:
        pdf = _BoldPDF(brand=brand, running_title=job, accent=accent)
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
        if sig:
            _signature(pdf, sig, accent)
        return bytes(pdf.output())
