from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any

from docx import Document as WordDocument
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
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

ORANGE = "#F47A20"
DARK_ORANGE = "#C97800"
CHARCOAL = "#30343B"
MUTED = "#6B7280"
LIGHT_LINE = "#D9DDE2"
FOOTER_BG = "#F7F8F9"
WHITE = "#FFFFFF"

LETTERHEAD_NAME = "GUARDRISK INSURANCE BROKERS"
SERVICE_LINE = "Financial Planning | Insurance | Risk Advisory"
ADDRESS_LINE = "LNDC CENTRE, GROUND FLOOR"
LOCATION_LINE = "Kingsway, Maseru 100, Lesotho"
PHONE_LINE = "(+266) 2232 2537 / 5939 5332 / 6272 0488"
EMAIL_LINE = "info@guardrisk.co.ls"
IBR_LINE = "IBR No. 69915"


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def official_settings(value: dict[str, Any] | None) -> dict[str, Any]:
    """Return Studio settings with the agreed Guardrisk stationery locked on."""
    settings = dict(value or {})
    settings["brand_header"] = True
    settings["official_letterhead"] = "guardrisk_premium_v2"
    return settings


def _export_proxy(document: StudioDocument) -> SimpleNamespace:
    settings = official_settings(document.settings)
    # The existing rich exporters render the editable document body. Reserve
    # enough page space for the fixed corporate stationery and suppress their
    # legacy mini-header before the premium stationery is applied.
    settings["brand_header"] = False
    settings["margin_top_mm"] = max(68.0, _number(settings.get("margin_top_mm"), 20.0) + 48.0)
    settings["margin_bottom_mm"] = max(25.0, _number(settings.get("margin_bottom_mm"), 20.0) + 8.0)
    settings["margin_left_mm"] = max(22.0, _number(settings.get("margin_left_mm"), 20.0))
    settings["margin_right_mm"] = max(18.0, _number(settings.get("margin_right_mm"), 20.0))
    return SimpleNamespace(
        title=document.title,
        style_key=document.style_key,
        html_content=document.html_content,
        settings=settings,
        version=document.version,
    )


def _draw_pdf_letterhead(canvas: pdf_canvas.Canvas, width: float, height: float) -> None:
    orange = colors.HexColor(ORANGE)
    dark_orange = colors.HexColor(DARK_ORANGE)
    charcoal = colors.HexColor(CHARCOAL)
    muted = colors.HexColor(MUTED)
    light_line = colors.HexColor(LIGHT_LINE)
    footer_bg = colors.HexColor(FOOTER_BG)

    # Premium top bands.
    canvas.setFillColor(orange)
    canvas.rect(0, height - 4.5 * mm, width, 4.5 * mm, stroke=0, fill=1)
    canvas.setFillColor(dark_orange)
    path = canvas.beginPath()
    path.moveTo(0, height - 4.5 * mm)
    path.lineTo(36 * mm, height - 4.5 * mm)
    path.lineTo(29 * mm, height - 12 * mm)
    path.lineTo(0, height - 12 * mm)
    path.close()
    canvas.drawPath(path, stroke=0, fill=1)

    # Left logo and business identity.
    logo_x = 24 * mm
    logo_y = height - 31 * mm
    canvas.setFillColor(orange)
    canvas.circle(logo_x, logo_y, 7.4 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(logo_x, logo_y - 4.2, "G")

    brand_x = 39 * mm
    canvas.setFillColor(orange)
    canvas.setFont("Helvetica-Bold", 15.5)
    canvas.drawString(brand_x, height - 28.5 * mm, "GUARDRISK")
    canvas.setFillColor(charcoal)
    canvas.setFont("Helvetica-Bold", 6.8)
    canvas.drawString(brand_x, height - 34 * mm, "INSURANCE BROKERS")
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 6.3)
    canvas.drawString(brand_x, height - 39 * mm, SERVICE_LINE)

    # Right contact block.
    right = width - 18 * mm
    canvas.setFillColor(charcoal)
    canvas.setFont("Helvetica-Bold", 7.2)
    canvas.drawRightString(right, height - 23.5 * mm, ADDRESS_LINE)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawRightString(right, height - 29 * mm, LOCATION_LINE)
    canvas.drawRightString(right, height - 34.5 * mm, PHONE_LINE)
    canvas.drawRightString(right, height - 40 * mm, EMAIL_LINE)
    canvas.setFillColor(charcoal)
    canvas.setFont("Helvetica-Bold", 6.6)
    canvas.drawRightString(right, height - 45 * mm, IBR_LINE)

    # Divider and correspondence metadata row.
    left = 18 * mm
    rule_y = height - 51 * mm
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(1.5)
    canvas.line(left, rule_y, 47 * mm, rule_y)
    canvas.setStrokeColor(light_line)
    canvas.setLineWidth(0.55)
    canvas.line(47 * mm, rule_y, right, rule_y)

    meta_y = height - 63 * mm
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica-Bold", 6.2)
    canvas.drawString(left, meta_y, "DATE")
    canvas.drawString(81 * mm, meta_y, "REFERENCE")
    canvas.setFont("Helvetica", 6.2)
    canvas.drawRightString(right, meta_y, "OFFICIAL CORRESPONDENCE")
    canvas.setStrokeColor(light_line)
    canvas.setLineWidth(0.45)
    canvas.line(31 * mm, meta_y - 1.2 * mm, 68 * mm, meta_y - 1.2 * mm)
    canvas.line(101 * mm, meta_y - 1.2 * mm, 145 * mm, meta_y - 1.2 * mm)

    # Signature vertical accent from the approved stationery.
    side_x = 18 * mm
    footer_top = 20 * mm
    side_top = height - 92 * mm
    side_bottom = footer_top + 28 * mm
    if side_top > side_bottom:
        canvas.setStrokeColor(light_line)
        canvas.setLineWidth(0.55)
        canvas.line(side_x, side_bottom, side_x, side_top)
        canvas.setStrokeColor(orange)
        canvas.setLineWidth(1.5)
        canvas.line(side_x, side_top - 25 * mm, side_x, side_top)

    # Fixed premium footer. Its background also masks the legacy page-number footer.
    canvas.setFillColor(footer_bg)
    canvas.rect(0, 0, width, 19 * mm, stroke=0, fill=1)
    canvas.setFillColor(orange)
    canvas.rect(0, 19 * mm, width, 1.25 * mm, stroke=0, fill=1)

    footer_left = 18 * mm
    canvas.setFillColor(charcoal)
    canvas.setFont("Helvetica-Bold", 6.2)
    canvas.drawString(footer_left, 11.5 * mm, LETTERHEAD_NAME)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 5.8)
    canvas.drawString(
        footer_left,
        6.2 * mm,
        "LNDC Centre, Ground Floor Kingsway, Maseru 100 | " + PHONE_LINE,
    )

    footer_right = width - 20 * mm
    canvas.setFont("Helvetica", 5.8)
    canvas.drawRightString(footer_right, 11.5 * mm, f"{EMAIL_LINE}  |  {IBR_LINE}")
    canvas.setFillColor(orange)
    canvas.circle(width - 11 * mm, 6.2 * mm, 3.5 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 6.5)
    canvas.drawCentredString(width - 11 * mm, 5.3 * mm, "G")


def export_pdf(document: StudioDocument) -> bytes:
    """Export rich PDF content with the approved letterhead/footer on every page."""
    source = export_base_pdf(_export_proxy(document))
    reader = PdfReader(BytesIO(source))
    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = pdf_canvas.Canvas(overlay_buffer, pagesize=(width, height))
        _draw_pdf_letterhead(overlay_canvas, width, height)
        overlay_canvas.save()
        overlay_buffer.seek(0)
        overlay_page = PdfReader(overlay_buffer).pages[0]
        page.merge_page(overlay_page, over=True)
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


def _shade_cell(cell: Any, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill.lstrip("#"))


def _cell_bottom_border(cell: Any, color: str, size: str = "6") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    bottom = borders.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        borders.append(bottom)
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:color"), color.lstrip("#"))


def _zero_cell_margins(cell: Any) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for side in ("top", "start", "bottom", "end"):
        node = margins.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            margins.append(node)
        node.set(qn("w:w"), "0")
        node.set(qn("w:type"), "dxa")


def _format_run(run: Any, *, size: float, bold: bool = False, color: str = CHARCOAL) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))


def _add_header(section: Any) -> None:
    header = section.header
    header.is_linked_to_previous = False
    _clear_story(header)
    available = section.page_width - section.left_margin - section.right_margin

    stripe = header.add_table(rows=1, cols=1, width=available)
    stripe.alignment = WD_TABLE_ALIGNMENT.CENTER
    stripe.rows[0].height = Mm(3.8)
    stripe.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    _shade_cell(stripe.cell(0, 0), ORANGE)
    _zero_cell_margins(stripe.cell(0, 0))

    identity = header.add_table(rows=1, cols=2, width=available)
    identity.alignment = WD_TABLE_ALIGNMENT.CENTER
    identity.autofit = False
    left, right = identity.rows[0].cells
    left.width = available * 0.56
    right.width = available * 0.44
    left.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    brand = left.paragraphs[0]
    brand.paragraph_format.space_after = Pt(0)
    g_run = brand.add_run("G   ")
    _format_run(g_run, size=14, bold=True, color=ORANGE)
    name_run = brand.add_run("GUARDRISK")
    _format_run(name_run, size=14, bold=True, color=ORANGE)
    broker = left.add_paragraph()
    broker.paragraph_format.space_after = Pt(0)
    _format_run(broker.add_run("INSURANCE BROKERS"), size=6.8, bold=True)
    services = left.add_paragraph()
    services.paragraph_format.space_after = Pt(0)
    _format_run(services.add_run(SERVICE_LINE), size=6.2, color=MUTED)

    contact = right.paragraphs[0]
    contact.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    contact.paragraph_format.space_after = Pt(0)
    for index, (text, bold, color) in enumerate(
        (
            (ADDRESS_LINE, True, CHARCOAL),
            (LOCATION_LINE, False, MUTED),
            (PHONE_LINE, False, MUTED),
            (EMAIL_LINE, False, MUTED),
            (IBR_LINE, True, CHARCOAL),
        )
    ):
        run = contact.add_run(text)
        _format_run(run, size=6.3 if not bold else 6.6, bold=bold, color=color)
        if index < 4:
            run.add_break()

    rule = header.add_table(rows=1, cols=2, width=available)
    rule.alignment = WD_TABLE_ALIGNMENT.CENTER
    rule.autofit = False
    rule.rows[0].height = Mm(0.8)
    rule.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    rule.cells[0].width = Mm(29)
    rule.cells[1].width = available - Mm(29)
    for cell in rule.rows[0].cells:
        _zero_cell_margins(cell)
    _shade_cell(rule.cell(0, 0), ORANGE)
    _shade_cell(rule.cell(0, 1), LIGHT_LINE)

    meta = header.add_table(rows=1, cols=3, width=available)
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta.autofit = False
    for cell in meta.rows[0].cells:
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    entries = (("DATE", True), ("REFERENCE", True), ("OFFICIAL CORRESPONDENCE", False))
    for cell, (label, underline) in zip(meta.rows[0].cells, entries, strict=True):
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        if label == "OFFICIAL CORRESPONDENCE":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _format_run(paragraph.add_run(label), size=6.2, bold=underline, color=MUTED)
        if underline:
            _cell_bottom_border(cell, LIGHT_LINE, "4")


def _add_footer(section: Any) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    _clear_story(footer)
    available = section.page_width - section.left_margin - section.right_margin

    rule = footer.add_table(rows=1, cols=1, width=available)
    rule.alignment = WD_TABLE_ALIGNMENT.CENTER
    rule.rows[0].height = Mm(1.2)
    rule.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
    _shade_cell(rule.cell(0, 0), ORANGE)
    _zero_cell_margins(rule.cell(0, 0))

    table = footer.add_table(rows=1, cols=2, width=available)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    left, right = table.rows[0].cells
    left.width = available * 0.67
    right.width = available * 0.33
    _shade_cell(left, FOOTER_BG)
    _shade_cell(right, FOOTER_BG)

    left_paragraph = left.paragraphs[0]
    left_paragraph.paragraph_format.space_after = Pt(0)
    _format_run(left_paragraph.add_run(LETTERHEAD_NAME), size=6.2, bold=True)
    address = left.add_paragraph()
    address.paragraph_format.space_after = Pt(0)
    _format_run(
        address.add_run("LNDC Centre, Ground Floor Kingsway, Maseru 100 | " + PHONE_LINE),
        size=5.6,
        color=MUTED,
    )

    right_paragraph = right.paragraphs[0]
    right_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right_paragraph.paragraph_format.space_after = Pt(0)
    _format_run(right_paragraph.add_run(f"{EMAIL_LINE}  |  {IBR_LINE}"), size=5.7, color=MUTED)
    logo = right.add_paragraph()
    logo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    logo.paragraph_format.space_after = Pt(0)
    _format_run(logo.add_run("G"), size=8, bold=True, color=ORANGE)


def export_docx(document: StudioDocument) -> bytes:
    """Export editable DOCX with the agreed stationery repeated on every page."""
    source = export_base_docx(_export_proxy(document))
    word = WordDocument(BytesIO(source))
    for section in word.sections:
        section.top_margin = Mm(68)
        section.bottom_margin = Mm(25)
        section.left_margin = Mm(max(22.0, _number((document.settings or {}).get("margin_left_mm"), 20.0)))
        section.right_margin = Mm(max(18.0, _number((document.settings or {}).get("margin_right_mm"), 20.0)))
        section.header_distance = Mm(2)
        section.footer_distance = Mm(2)
        _add_header(section)
        _add_footer(section)

    core = word.core_properties
    core.author = "Guardrisk Insurance Brokers"
    core.subject = "Official Guardrisk correspondence"
    core.comments = "Generated by gRisk Document Studio using Guardrisk Premium Letterhead V2"
    output = BytesIO()
    word.save(output)
    return output.getvalue()
