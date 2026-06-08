"""Classic Serif template.

Conservative typesetting using Times for headings and body, minimal accent
(thin rules only), generous whitespace, centred cover. Designed for
enterprise / legal / government audiences where loud branding hurts.
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


class _ClassicPDF(FPDF):
    def __init__(self, *, brand: str, running_title: str, accent: tuple[int, int, int]) -> None:
        super().__init__(format="A4")
        self._brand = brand
        self._running_title = running_title
        self._accent = accent
        self.set_margins(22, 22, 22)
        self.set_auto_page_break(True, margin=22)

    def header(self) -> None:  # noqa: D102
        if self.page_no() == 1:
            return
        self.set_font("Times", "I", 9)
        self.set_text_color(110)
        self.cell(0, 6, self._running_title[:70])
        if self._brand:
            self.cell(0, 6, self._brand, align="R")
        self.ln(7)
        # Hairline rule under the running header.
        self.set_draw_color(180)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(0)

    def footer(self) -> None:  # noqa: D102
        self.set_y(-15)
        self.set_font("Times", "", 9)
        self.set_text_color(120)
        if self._brand:
            self.cell(0, 6, self._brand, align="L")
        self.cell(0, 6, f"-- {self.page_no()} --", align="R")
        self.set_text_color(0)


def _cover(
    pdf: _ClassicPDF,
    *,
    job_title: str,
    client: str,
    brand: str,
    intro: str,
    accent: tuple[int, int, int],
    logo: Path | None,
) -> None:
    pdf.ln(18)

    if logo is not None and logo.exists():
        # Centred logo above the title.
        try:
            pdf.image(str(logo), x=(pdf.w - 28) / 2, y=pdf.get_y(), h=22)
            pdf.ln(28)
        except Exception:
            pass

    # Tagline.
    pdf.set_font("Times", "", 11)
    pdf.set_text_color(100)
    pdf.cell(0, 6, "PROJECT PROPOSAL", align="C")
    pdf.ln(10)

    pdf.set_font("Times", "B", 24)
    pdf.set_text_color(20)
    pdf.multi_cell(0, 10, job_title or "Proposal", align="C")
    pdf.ln(2)

    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.4)
    mid_y = pdf.get_y() + 4
    pdf.line(pdf.w / 2 - 18, mid_y, pdf.w / 2 + 18, mid_y)
    pdf.ln(10)

    pdf.set_font("Times", "", 11)
    pdf.set_text_color(80)
    for label, value in (
        ("Prepared for", client),
        ("Prepared by", brand),
        ("Date", date.today().strftime("%B %d, %Y")),
    ):
        if value:
            pdf.cell(0, 6, f"{label}: {value}", align="C")
            pdf.ln(6)

    if intro:
        pdf.ln(6)
        pdf.set_font("Times", "I", 11)
        pdf.set_text_color(70)
        pdf.multi_cell(0, 5.6, intro, align="C")

    pdf.ln(8)
    pdf.set_draw_color(160)
    pdf.set_line_width(0.2)
    y = pdf.get_y()
    pdf.line(pdf.l_margin + 30, y, pdf.w - pdf.r_margin - 30, y)
    pdf.ln(8)
    pdf.set_text_color(0)


def _table(pdf, payload, accent) -> None:
    header = payload.get("header") or []
    rows = payload.get("rows") or []
    if not header:
        return
    pdf.ln(2)
    pdf.set_font("Times", "", 10.5)
    heading_style = FontFace(emphasis="BOLD", color=(40, 40, 40), size_pt=10.5)
    link_cell_style = FontFace(emphasis="UNDERLINE", color=accent)
    with pdf.table(
        text_align="LEFT",
        line_height=5.6,
        headings_style=heading_style,
        cell_fill_color=(248, 248, 248),
        cell_fill_mode=TableCellFillMode.ROWS,
        borders_layout="HORIZONTAL_LINES",
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
    # Subtle accent rule under the table.
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + 30, y)
    pdf.ln(3)


def _body(pdf: _ClassicPDF, elements, accent) -> None:
    for kind, content in elements:
        pdf.set_x(pdf.l_margin)
        if kind == "space":
            pdf.ln(2.5)
        elif kind == "heading":
            pdf.ln(4)
            pdf.set_font("Times", "B", 14)
            pdf.set_text_color(30)
            pdf.multi_cell(0, 7, content)
            pdf.set_draw_color(*accent)
            pdf.set_line_width(0.4)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.l_margin + 30, y)
            pdf.ln(3)
        elif kind == "subheading":
            pdf.ln(2)
            pdf.set_font("Times", "B", 11.5)
            pdf.set_text_color(50)
            pdf.multi_cell(0, 6, content)
            pdf.set_text_color(0)
        elif kind == "bullet":
            pdf.set_font("Times", "", 11)
            saved = pdf.l_margin
            pdf.set_left_margin(saved + 6)
            pdf.set_x(saved + 6)
            write_inline_runs(pdf, f"- {content}", 6, accent)
            pdf.set_left_margin(saved)
            pdf.set_x(saved)
        elif kind == "table":
            _table(pdf, content, accent)
        else:
            pdf.set_font("Times", "", 11)
            pdf.set_text_color(40)
            write_inline_runs(pdf, content, 6, accent)
            pdf.ln(1.5)


def _signature(pdf: _ClassicPDF, signature: str, accent) -> None:
    pdf.ln(8)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + 60, y)
    pdf.ln(2)
    pdf.set_font("Times", "I", 10)
    pdf.set_text_color(70)
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
        pdf = _ClassicPDF(brand=brand, running_title=job, accent=accent)
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
