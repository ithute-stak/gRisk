from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any

from docx import Document as WordDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
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

ORANGE = "#F15A24"
PEACH = "#F7B38C"
CHARCOAL = "#344054"
MUTED = "#667085"
LINE = "#D0D5DD"
WHITE = "#FFFFFF"

DEFAULT_ADDRESS = "LNDC Centre, Ground Floor, Shop No. ____"
DEFAULT_PHONE_1 = "+266 2232 2537"
DEFAULT_PHONE_2 = "+266 6272 0488"
DEFAULT_EMAIL = "info@guardrisk.co.ls"
DEFAULT_FOOTER_LEFT = "GUARDRISK HEALTH"
DEFAULT_FOOTER_RIGHT = "LOW COST MEDICAL AID"


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_lesotho_phone(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    digits = "".join(character for character in text if character.isdigit())
    if digits.startswith("266"):
        local = digits[3:]
    elif digits.startswith("0"):
        local = digits[1:]
    else:
        local = digits
    if not local:
        return "+266"
    grouped = " ".join(local[index : index + 4] for index in range(0, len(local), 4))
    return f"+266 {grouped}"


def stationery_values(settings: dict[str, Any] | None) -> dict[str, str]:
    source = settings or {}
    return {
        "address": str(source.get("letterhead_address") or DEFAULT_ADDRESS),
        "phone_1": normalize_lesotho_phone(source.get("letterhead_phone_1") or DEFAULT_PHONE_1),
        "phone_2": normalize_lesotho_phone(source.get("letterhead_phone_2") or DEFAULT_PHONE_2),
        "email": str(source.get("letterhead_email") or DEFAULT_EMAIL),
        "footer_left": str(source.get("letterhead_footer_left") or DEFAULT_FOOTER_LEFT),
        "footer_right": str(source.get("letterhead_footer_right") or DEFAULT_FOOTER_RIGHT),
    }


def official_settings(value: dict[str, Any] | None) -> dict[str, Any]:
    settings = dict(value or {})
    settings["brand_header"] = True
    settings["official_letterhead"] = "guardrisk_sketch_v3"
    details = stationery_values(settings)
    settings["letterhead_address"] = details["address"]
    settings["letterhead_phone_1"] = details["phone_1"]
    settings["letterhead_phone_2"] = details["phone_2"]
    settings["letterhead_email"] = details["email"]
    settings["letterhead_footer_left"] = details["footer_left"]
    settings["letterhead_footer_right"] = details["footer_right"]
    return settings


def _export_proxy(document: StudioDocument) -> SimpleNamespace:
    settings = official_settings(document.settings)
    settings["brand_header"] = False
    settings["margin_top_mm"] = max(60.0, _number(settings.get("margin_top_mm"), 20.0) + 40.0)
    settings["margin_bottom_mm"] = max(38.0, _number(settings.get("margin_bottom_mm"), 20.0) + 18.0)
    settings["margin_left_mm"] = max(18.0, _number(settings.get("margin_left_mm"), 20.0))
    settings["margin_right_mm"] = max(18.0, _number(settings.get("margin_right_mm"), 20.0))
    return SimpleNamespace(
        title=document.title,
        style_key=document.style_key,
        html_content=document.html_content,
        settings=settings,
        version=document.version,
    )


def _draw_pdf_stationery(canvas: pdf_canvas.Canvas, width: float, height: float, details: dict[str, str]) -> None:
    orange = colors.HexColor(ORANGE)
    peach = colors.HexColor(PEACH)
    charcoal = colors.HexColor(CHARCOAL)
    muted = colors.HexColor(MUTED)
    line = colors.HexColor(LINE)

    # Top-left curved accent inspired by the approved sketch.
    canvas.setFillColor(orange)
    path = canvas.beginPath()
    path.moveTo(0, height)
    path.lineTo(76 * mm, height)
    path.curveTo(52 * mm, height - 2 * mm, 26 * mm, height - 9 * mm, 0, height - 20 * mm)
    path.close()
    canvas.drawPath(path, stroke=0, fill=1)
    canvas.setStrokeColor(peach)
    canvas.setLineWidth(1.8)
    canvas.bezier(0, height - 20 * mm, 25 * mm, height - 9 * mm, 48 * mm, height - 4 * mm, 73 * mm, height - 1 * mm)

    # Centered Guardrisk identity.
    center = width / 2
    canvas.setFillColor(orange)
    canvas.circle(center, height - 12 * mm, 8.2 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(center, height - 15.1 * mm, "G")
    canvas.setFillColor(orange)
    canvas.setFont("Times-Bold", 20)
    canvas.drawCentredString(center, height - 29 * mm, "GUARDRISK")
    canvas.setFillColor(charcoal)
    canvas.setFont("Helvetica", 6.8)
    canvas.drawCentredString(center, height - 34.3 * mm, "D O C U M E N T   S T U D I O")

    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.8)
    canvas.line(18 * mm, height - 43 * mm, 60 * mm, height - 43 * mm)
    canvas.line(width - 60 * mm, height - 43 * mm, width - 18 * mm, height - 43 * mm)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(center, height - 44.3 * mm, "YOUR LINK TO PREMIER HEALTHCARE")

    # Editable address at the upper right.
    right = width - 18 * mm
    canvas.setFillColor(charcoal)
    canvas.setFont("Helvetica-Bold", 6.6)
    canvas.drawRightString(right - 42 * mm, height - 49 * mm, "Address:")
    canvas.setFont("Helvetica", 6.6)
    address = details["address"]
    chunks = [address[index : index + 45] for index in range(0, len(address), 45)] or [""]
    for index, chunk in enumerate(chunks[:2]):
        canvas.drawString(right - 40 * mm, height - (49 + index * 4) * mm, chunk)

    # Footer contact line and labels.
    footer_top = 34 * mm
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, footer_top, stroke=0, fill=1)
    canvas.setStrokeColor(line)
    canvas.setLineWidth(0.45)
    canvas.line(18 * mm, 30 * mm, width - 18 * mm, 30 * mm)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 5.8)
    canvas.drawString(18 * mm, 24 * mm, f"Address: {details['address']}")
    canvas.drawCentredString(center, 24 * mm, f"Call: {details['phone_1']} / {details['phone_2']}")
    canvas.drawRightString(width - 18 * mm, 24 * mm, f"Email: {details['email']}")
    canvas.setFont("Helvetica-Bold", 5.4)
    canvas.drawString(18 * mm, 17 * mm, details["footer_left"].upper())
    canvas.drawRightString(width - 18 * mm, 17 * mm, details["footer_right"].upper())

    # Bottom orange wave.
    canvas.setFillColor(orange)
    wave = canvas.beginPath()
    wave.moveTo(0, 12 * mm)
    wave.curveTo(34 * mm, 3 * mm, 64 * mm, 9 * mm, 94 * mm, 12 * mm)
    wave.curveTo(125 * mm, 15 * mm, 148 * mm, 5 * mm, 177 * mm, 7 * mm)
    wave.curveTo(194 * mm, 8 * mm, 204 * mm, 12 * mm, width, 15 * mm)
    wave.lineTo(width, 0)
    wave.lineTo(0, 0)
    wave.close()
    canvas.drawPath(wave, stroke=0, fill=1)
    canvas.setStrokeColor(peach)
    canvas.setLineWidth(2)
    canvas.bezier(0, 14 * mm, 34 * mm, 5 * mm, 64 * mm, 11 * mm, 94 * mm, 14 * mm)
    canvas.bezier(94 * mm, 14 * mm, 126 * mm, 17 * mm, 150 * mm, 7 * mm, width, 17 * mm)


def export_pdf(document: StudioDocument) -> bytes:
    source = export_base_pdf(_export_proxy(document))
    details = stationery_values(document.settings)
    reader = PdfReader(BytesIO(source))
    writer = PdfWriter()
    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = pdf_canvas.Canvas(overlay_buffer, pagesize=(width, height))
        _draw_pdf_stationery(overlay_canvas, width, height, details)
        overlay_canvas.save()
        overlay_buffer.seek(0)
        page.merge_page(PdfReader(overlay_buffer).pages[0], over=True)
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata({key: str(value) for key, value in reader.metadata.items() if value is not None})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _set_run(run: Any, *, size: float, bold: bool = False, color: str = CHARCOAL) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))


def _top_border(cell: Any, color: str = LINE) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    top = borders.find(qn("w:top"))
    if top is None:
        top = OxmlElement("w:top")
        borders.append(top)
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), "4")
    top.set(qn("w:color"), color.lstrip("#"))


def _clear_story(container: Any) -> None:
    element = container._element
    for child in list(element):
        element.remove(child)


def _add_docx_header(section: Any, details: dict[str, str]) -> None:
    header = section.header
    header.is_linked_to_previous = False
    _clear_story(header)

    logo = header.add_paragraph()
    logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo.paragraph_format.space_after = Pt(0)
    _set_run(logo.add_run("G"), size=18, bold=True, color=ORANGE)

    brand = header.add_paragraph()
    brand.alignment = WD_ALIGN_PARAGRAPH.CENTER
    brand.paragraph_format.space_after = Pt(0)
    _set_run(brand.add_run("GUARDRISK"), size=17, bold=True, color=ORANGE)

    studio = header.add_paragraph()
    studio.alignment = WD_ALIGN_PARAGRAPH.CENTER
    studio.paragraph_format.space_after = Pt(1)
    _set_run(studio.add_run("D O C U M E N T   S T U D I O"), size=6.5, color=CHARCOAL)

    tagline = header.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tagline.paragraph_format.space_after = Pt(2)
    _set_run(tagline.add_run("YOUR LINK TO PREMIER HEALTHCARE"), size=6.2, color=MUTED)

    address = header.add_paragraph()
    address.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    address.paragraph_format.space_after = Pt(0)
    _set_run(address.add_run("Address: "), size=6.3, bold=True)
    _set_run(address.add_run(details["address"]), size=6.3, color=MUTED)


def _add_docx_footer(section: Any, details: dict[str, str]) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    _clear_story(footer)
    available = section.page_width - section.left_margin - section.right_margin
    table = footer.add_table(rows=1, cols=3, width=available)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    values = (
        f"Address: {details['address']}",
        f"Call: {details['phone_1']} / {details['phone_2']}",
        f"Email: {details['email']}",
    )
    for cell, value in zip(table.rows[0].cells, values, strict=True):
        _top_border(cell)
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        _set_run(paragraph.add_run(value), size=5.6, color=MUTED)

    labels = footer.add_paragraph()
    labels.paragraph_format.space_before = Pt(2)
    labels.paragraph_format.space_after = Pt(0)
    _set_run(labels.add_run(details["footer_left"].upper()), size=5.5, bold=True, color=MUTED)
    labels.add_run(" " * 20)
    right = labels.add_run(details["footer_right"].upper())
    _set_run(right, size=5.5, bold=True, color=ORANGE)


def export_docx(document: StudioDocument) -> bytes:
    source = export_base_docx(_export_proxy(document))
    details = stationery_values(document.settings)
    word = WordDocument(BytesIO(source))
    for section in word.sections:
        section.top_margin = Mm(60)
        section.bottom_margin = Mm(38)
        section.left_margin = Mm(max(18.0, _number((document.settings or {}).get("margin_left_mm"), 20.0)))
        section.right_margin = Mm(max(18.0, _number((document.settings or {}).get("margin_right_mm"), 20.0)))
        section.header_distance = Mm(3)
        section.footer_distance = Mm(3)
        _add_docx_header(section, details)
        _add_docx_footer(section, details)

    core = word.core_properties
    core.author = "Guardrisk Insurance Brokers"
    core.subject = "Official Guardrisk correspondence"
    core.comments = "Generated by gRisk Document Studio using editable Guardrisk stationery"
    output = BytesIO()
    word.save(output)
    return output.getvalue()
