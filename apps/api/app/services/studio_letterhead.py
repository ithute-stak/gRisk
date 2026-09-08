from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any

from docx import Document as WordDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas

from app.models.studio import StudioDocument
from app.services.studio_export import export_docx as export_base_docx
from app.services.studio_export import export_pdf as export_base_pdf

BLUE = "#1F4E79"
GOLD = "#D6A11D"
MUTED = "#667085"

LETTERHEAD_NAME = "GUARDRISK"
LETTERHEAD_SUBTITLE = "INSURANCE BROKERS"
FOOTER_LINE = (
    "Guardrisk Insurance Brokers | LNDC Centre, Kingsway, Maseru 100 | "
    "info@guardrisk.co.ls | +266 2232 2537 / 6272 0488"
)


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def official_settings(value: dict[str, Any] | None) -> dict[str, Any]:
    settings = dict(value or {})
    settings["brand_header"] = True
    settings["official_letterhead"] = "guardrisk_minimal_v3"
    return settings


def _export_proxy(document: StudioDocument) -> SimpleNamespace:
    settings = official_settings(document.settings)
    settings["brand_header"] = False
    settings["margin_top_mm"] = max(40.0, _number(settings.get("margin_top_mm"), 20.0) + 20.0)
    settings["margin_bottom_mm"] = max(16.0, _number(settings.get("margin_bottom_mm"), 20.0))
    settings["margin_left_mm"] = max(20.0, _number(settings.get("margin_left_mm"), 20.0))
    settings["margin_right_mm"] = max(20.0, _number(settings.get("margin_right_mm"), 20.0))
    return SimpleNamespace(
        title=document.title,
        style_key=document.style_key,
        html_content=document.html_content,
        settings=settings,
        version=document.version,
    )


def _draw_pdf_stationery(canvas: pdf_canvas.Canvas, width: float, height: float) -> None:
    blue = colors.HexColor(BLUE)
    gold = colors.HexColor(GOLD)
    muted = colors.HexColor(MUTED)
    center = width / 2

    logo_y = height - 10 * mm
    canvas.setStrokeColor(gold)
    canvas.setLineWidth(0.75)
    canvas.circle(center, logo_y, 5.5 * mm, stroke=1, fill=0)
    canvas.setFillColor(blue)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawCentredString(center, logo_y - 5, "G")

    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(center, height - 20.5 * mm, LETTERHEAD_NAME)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(center, height - 26 * mm, LETTERHEAD_SUBTITLE)

    canvas.setStrokeColor(gold)
    canvas.setLineWidth(0.7)
    canvas.line(18 * mm, height - 31 * mm, width - 18 * mm, height - 31 * mm)

    canvas.setStrokeColor(gold)
    canvas.setLineWidth(0.45)
    canvas.line(18 * mm, 11 * mm, width - 18 * mm, 11 * mm)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 5.4)
    canvas.drawCentredString(center, 6.5 * mm, FOOTER_LINE)


def export_pdf(document: StudioDocument) -> bytes:
    source = export_base_pdf(_export_proxy(document))
    reader = PdfReader(BytesIO(source))
    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = pdf_canvas.Canvas(overlay_buffer, pagesize=(width, height))
        _draw_pdf_stationery(overlay_canvas, width, height)
        overlay_canvas.save()
        overlay_buffer.seek(0)
        page.merge_page(PdfReader(overlay_buffer).pages[0], over=True)
        writer.add_page(page)

    if reader.metadata:
        writer.add_metadata({key: str(value) for key, value in reader.metadata.items() if value is not None})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _clear_story(container: Any) -> None:
    element = container._element
    for child in list(element):
        element.remove(child)


def _format_run(run: Any, *, size: float, bold: bool = False, color: str = MUTED) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))


def _paragraph_bottom_border(paragraph: Any, color: str, size: str = "6") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        p_pr.append(borders)
    bottom = borders.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        borders.append(bottom)
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), color.lstrip("#"))


def _paragraph_top_border(paragraph: Any, color: str, size: str = "4") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = p_pr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        p_pr.append(borders)
    top = borders.find(qn("w:top"))
    if top is None:
        top = OxmlElement("w:top")
        borders.append(top)
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), size)
    top.set(qn("w:space"), "3")
    top.set(qn("w:color"), color.lstrip("#"))


def _add_header(section: Any) -> None:
    header = section.header
    header.is_linked_to_previous = False
    _clear_story(header)

    logo = header.add_paragraph()
    logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo.paragraph_format.space_after = Pt(0)
    _format_run(logo.add_run("◯  G"), size=10, bold=True, color=BLUE)

    brand = header.add_paragraph()
    brand.alignment = WD_ALIGN_PARAGRAPH.CENTER
    brand.paragraph_format.space_after = Pt(0)
    _format_run(brand.add_run(LETTERHEAD_NAME), size=12, bold=True, color=BLUE)

    subtitle = header.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(2)
    _format_run(subtitle.add_run(LETTERHEAD_SUBTITLE), size=6.5, color=MUTED)
    _paragraph_bottom_border(subtitle, GOLD, "6")


def _add_footer(section: Any) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    _clear_story(footer)

    line = footer.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    line.paragraph_format.space_before = Pt(0)
    line.paragraph_format.space_after = Pt(0)
    _paragraph_top_border(line, GOLD, "4")
    _format_run(line.add_run(FOOTER_LINE), size=5.5, color=MUTED)


def export_docx(document: StudioDocument) -> bytes:
    source = export_base_docx(_export_proxy(document))
    word = WordDocument(BytesIO(source))
    for section in word.sections:
        section.top_margin = Mm(40)
        section.bottom_margin = Mm(16)
        section.left_margin = Mm(max(20.0, _number((document.settings or {}).get("margin_left_mm"), 20.0)))
        section.right_margin = Mm(max(20.0, _number((document.settings or {}).get("margin_right_mm"), 20.0)))
        section.header_distance = Mm(3)
        section.footer_distance = Mm(4)
        _add_header(section)
        _add_footer(section)

    core = word.core_properties
    core.author = "Guardrisk Insurance Brokers"
    core.subject = "Official Guardrisk correspondence"
    core.comments = "Generated by gRisk Document Studio with compact Guardrisk stationery"
    output = BytesIO()
    word.save(output)
    return output.getvalue()
