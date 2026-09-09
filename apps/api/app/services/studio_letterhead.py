from __future__ import annotations

from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

from docx import Document as WordDocument
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
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

ORANGE = "#F23808"
PEACH = "#F7B38C"
NAVY = "#17345F"
MUTED = "#4B617F"
LINE = "#98A2B3"
WHITE = "#FFFFFF"

DEFAULT_ADDRESS_LINE_1 = "LNDC Centre, Ground Floor,"
DEFAULT_ADDRESS_LINE_2 = "Shop No. ____,"
DEFAULT_ADDRESS_LINE_3 = "Maseru 100, Lesotho"
DEFAULT_PHONE_1 = "+266 2232 2537"
DEFAULT_PHONE_2 = "+266 6272 0488"
DEFAULT_EMAIL = "info@guardrisk.co.ls"
DEFAULT_FOOTER_LEFT = "GUARDRISK HEALTH"
DEFAULT_FOOTER_RIGHT = "LOW COST MEDICAL AID"
DEFAULT_RECIPIENT = "Recipient Name"
DEFAULT_COMPANY = "Company Name"
DEFAULT_SUBJECT = "Your Subject Line Goes Here"
DEFAULT_TAGLINE = "YOUR LINK TO PREMIER HEALTHCARE"
DEFAULT_CLOSING_1 = "Kind regards,"
DEFAULT_CLOSING_2 = "For and on behalf of Guardrisk."
DEFAULT_SIGNER_NAME = "Your Name"
DEFAULT_SIGNER_TITLE = "Your Title"
DEFAULT_SIGNATURE_LABEL = "Click here to digitally sign"
DEFAULT_STAMP_LABEL = "Digital Stamp"


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


def _maseru_now() -> str:
    return datetime.now(ZoneInfo("Africa/Maseru")).strftime("%d %B %Y, %H:%M")


def _legacy_address_lines(source: dict[str, Any]) -> tuple[str, str, str]:
    legacy = str(source.get("letterhead_address") or "").replace("\r", "")
    pieces = [piece.strip() for piece in legacy.replace("\n", ",").split(",") if piece.strip()]
    line_1 = str(source.get("letterhead_address_line_1") or (pieces[0] if pieces else DEFAULT_ADDRESS_LINE_1))
    line_2 = str(source.get("letterhead_address_line_2") or (pieces[1] if len(pieces) > 1 else DEFAULT_ADDRESS_LINE_2))
    line_3 = str(
        source.get("letterhead_address_line_3")
        or (", ".join(pieces[2:]) if len(pieces) > 2 else DEFAULT_ADDRESS_LINE_3)
    )
    return line_1, line_2, line_3


def stationery_values(
    settings: dict[str, Any] | None,
    document: StudioDocument | None = None,
) -> dict[str, str]:
    del document
    source = settings or {}
    address_line_1, address_line_2, address_line_3 = _legacy_address_lines(source)
    address = "\n".join((address_line_1, address_line_2, address_line_3))
    return {
        "date_time": str(source.get("letterhead_date_time") or _maseru_now()),
        "recipient": str(source.get("letterhead_recipient") or DEFAULT_RECIPIENT),
        "company": str(source.get("letterhead_company") or DEFAULT_COMPANY),
        "address": address,
        "address_line_1": address_line_1,
        "address_line_2": address_line_2,
        "address_line_3": address_line_3,
        "subject": str(source.get("letterhead_subject") or DEFAULT_SUBJECT),
        "tagline": str(source.get("letterhead_tagline") or DEFAULT_TAGLINE),
        "phone_1": normalize_lesotho_phone(source.get("letterhead_phone_1") or DEFAULT_PHONE_1),
        "phone_2": normalize_lesotho_phone(source.get("letterhead_phone_2") or DEFAULT_PHONE_2),
        "email": str(source.get("letterhead_email") or DEFAULT_EMAIL),
        "footer_left": str(source.get("letterhead_footer_left") or DEFAULT_FOOTER_LEFT),
        "footer_right": str(source.get("letterhead_footer_right") or DEFAULT_FOOTER_RIGHT),
        "closing_line_1": str(source.get("letterhead_closing_line_1") or DEFAULT_CLOSING_1),
        "closing_line_2": str(source.get("letterhead_closing_line_2") or DEFAULT_CLOSING_2),
        "signer_name": str(source.get("letterhead_signer_name") or DEFAULT_SIGNER_NAME),
        "signer_title": str(source.get("letterhead_signer_title") or DEFAULT_SIGNER_TITLE),
        "signature_label": str(source.get("letterhead_signature_label") or DEFAULT_SIGNATURE_LABEL),
        "stamp_label": str(source.get("letterhead_stamp_label") or DEFAULT_STAMP_LABEL),
    }


def official_settings(
    value: dict[str, Any] | None,
    document: StudioDocument | None = None,
) -> dict[str, Any]:
    settings = dict(value or {})
    settings.pop("letterhead_code", None)
    settings["brand_header"] = True
    settings["official_letterhead"] = "guardrisk_reference_v6"
    details = stationery_values(settings, document)
    for key, detail in details.items():
        settings[f"letterhead_{key}"] = detail
    return settings


def _export_proxy(document: StudioDocument) -> SimpleNamespace:
    settings = official_settings(document.settings, document)
    settings["brand_header"] = False
    settings["margin_top_mm"] = max(101.0, _number(settings.get("margin_top_mm"), 20.0) + 81.0)
    settings["margin_bottom_mm"] = max(92.0, _number(settings.get("margin_bottom_mm"), 20.0) + 72.0)
    settings["margin_left_mm"] = max(18.0, _number(settings.get("margin_left_mm"), 20.0))
    settings["margin_right_mm"] = max(18.0, _number(settings.get("margin_right_mm"), 20.0))
    return SimpleNamespace(
        title=document.title,
        style_key=document.style_key,
        html_content=document.html_content,
        settings=settings,
        version=document.version,
    )


def _draw_label_value(
    canvas: pdf_canvas.Canvas,
    *,
    label: str,
    value: str,
    x: float,
    y: float,
    label_width: float = 23 * mm,
) -> None:
    canvas.setFillColor(colors.HexColor(NAVY))
    canvas.setFont("Helvetica-Bold", 7.2)
    canvas.drawString(x, y, label)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.setFont("Helvetica", 7.2)
    canvas.drawString(x + label_width, y, value)


def _draw_location_icon(canvas: pdf_canvas.Canvas, x: float, y: float) -> None:
    canvas.setFillColor(colors.HexColor(ORANGE))
    canvas.circle(x, y, 4.8 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(1.1)
    canvas.circle(x, y + 1.0 * mm, 1.6 * mm, stroke=1, fill=0)
    canvas.line(x, y - 3.0 * mm, x - 1.7 * mm, y - 0.4 * mm)
    canvas.line(x, y - 3.0 * mm, x + 1.7 * mm, y - 0.4 * mm)


def _draw_phone_icon(canvas: pdf_canvas.Canvas, x: float, y: float) -> None:
    canvas.setFillColor(colors.HexColor(ORANGE))
    canvas.circle(x, y, 4.8 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(2.1)
    canvas.arc(x - 2.8 * mm, y - 2.6 * mm, x + 2.8 * mm, y + 2.8 * mm, 205, 125)


def _draw_mail_icon(canvas: pdf_canvas.Canvas, x: float, y: float) -> None:
    canvas.setFillColor(colors.HexColor(ORANGE))
    canvas.circle(x, y, 4.8 * mm, stroke=0, fill=1)
    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(1.0)
    canvas.rect(x - 2.8 * mm, y - 1.9 * mm, 5.6 * mm, 3.8 * mm, stroke=1, fill=0)
    canvas.line(x - 2.8 * mm, y + 1.9 * mm, x, y - 0.4 * mm)
    canvas.line(x + 2.8 * mm, y + 1.9 * mm, x, y - 0.4 * mm)


def _draw_wave_footer(canvas: pdf_canvas.Canvas, width: float, details: dict[str, str]) -> None:
    orange = colors.HexColor(ORANGE)
    peach = colors.HexColor(PEACH)
    canvas.setFillColor(orange)
    wave = canvas.beginPath()
    wave.moveTo(0, 24 * mm)
    wave.curveTo(29 * mm, 33 * mm, 58 * mm, 26.5 * mm, 89 * mm, 23 * mm)
    wave.curveTo(120 * mm, 19.5 * mm, 145 * mm, 29.5 * mm, 174 * mm, 28 * mm)
    wave.curveTo(190 * mm, 27.2 * mm, 201 * mm, 23.6 * mm, width, 19.7 * mm)
    wave.lineTo(width, 0)
    wave.lineTo(0, 0)
    wave.close()
    canvas.drawPath(wave, stroke=0, fill=1)
    canvas.setStrokeColor(peach)
    canvas.setLineWidth(2.5)
    canvas.bezier(0, 20.5 * mm, 29 * mm, 29.5 * mm, 59 * mm, 23 * mm, 89.5 * mm, 19.7 * mm)
    canvas.bezier(89.5 * mm, 19.7 * mm, 120.5 * mm, 16.2 * mm, 145 * mm, 26 * mm, width, 16.7 * mm)
    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(1.2)
    canvas.bezier(0, 18.1 * mm, 29 * mm, 27.1 * mm, 59 * mm, 20.8 * mm, 89.5 * mm, 17.4 * mm)
    canvas.bezier(89.5 * mm, 17.4 * mm, 120.5 * mm, 14 * mm, 145.2 * mm, 23.8 * mm, width, 14.6 * mm)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 5.8)
    canvas.drawString(9.5 * mm, 5.5 * mm, details["footer_left"].upper())
    canvas.drawRightString(width - 9.5 * mm, 5.5 * mm, details["footer_right"].upper())


def _draw_pdf_header_footer(
    canvas: pdf_canvas.Canvas,
    width: float,
    height: float,
    details: dict[str, str],
) -> None:
    orange = colors.HexColor(ORANGE)
    navy = colors.HexColor(NAVY)
    muted = colors.HexColor(MUTED)
    line = colors.HexColor(LINE)
    center = width / 2

    canvas.setFillColor(orange)
    canvas.circle(center, height - 13 * mm, 9.5 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Bold", 28)
    canvas.drawCentredString(center, height - 17.3 * mm, "G")
    canvas.setFillColor(orange)
    canvas.setFont("Times-Bold", 24)
    canvas.drawCentredString(center, height - 31.5 * mm, "GUARDRISK")

    tagline_y = height - 42 * mm
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.8)
    canvas.line(9 * mm, tagline_y, 44 * mm, tagline_y)
    canvas.line(width - 44 * mm, tagline_y, width - 9 * mm, tagline_y)
    canvas.setStrokeColor(navy)
    canvas.line(46 * mm, tagline_y, 55 * mm, tagline_y)
    canvas.line(width - 55 * mm, tagline_y, width - 46 * mm, tagline_y)
    canvas.setFillColor(navy)
    canvas.setFont("Helvetica", 7.0)
    canvas.drawCentredString(center, tagline_y - 1.8, details["tagline"].upper())

    start_y = height - 56 * mm
    left = 10 * mm
    _draw_label_value(canvas, label="Date:", value=details["date_time"], x=left, y=start_y)
    _draw_label_value(canvas, label="To:", value=details["recipient"], x=left, y=start_y - 6 * mm)
    _draw_label_value(canvas, label="Company:", value=details["company"], x=left, y=start_y - 12 * mm)

    canvas.setStrokeColor(line)
    canvas.setLineWidth(0.45)
    canvas.line(center, height - 52 * mm, center, height - 79 * mm)

    right_x = center + 17 * mm
    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 7.2)
    canvas.drawString(right_x, start_y, "Address:")
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 7.2)
    for index, key in enumerate(("address_line_1", "address_line_2", "address_line_3")):
        canvas.drawString(right_x + 25 * mm, start_y - index * 6 * mm, details[key])

    subject_y = height - 87 * mm
    canvas.setFillColor(orange)
    canvas.setFont("Helvetica-Bold", 11.5)
    canvas.drawString(10 * mm, subject_y, "RE:")
    canvas.drawString(22 * mm, subject_y, details["subject"])
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.7)
    canvas.line(10 * mm, subject_y - 3.2 * mm, width - 10 * mm, subject_y - 3.2 * mm)

    contact_y = 39 * mm
    _draw_location_icon(canvas, 16 * mm, contact_y)
    _draw_phone_icon(canvas, 91 * mm, contact_y)
    _draw_mail_icon(canvas, 151 * mm, contact_y)

    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 5.8)
    canvas.drawString(28 * mm, contact_y + 3.6 * mm, details["address_line_1"])
    canvas.drawString(28 * mm, contact_y, details["address_line_2"])
    canvas.drawString(28 * mm, contact_y - 3.6 * mm, details["address_line_3"])
    canvas.drawString(103 * mm, contact_y + 2.2 * mm, details["phone_1"])
    canvas.drawString(103 * mm, contact_y - 2.2 * mm, details["phone_2"])
    canvas.drawString(163 * mm, contact_y, details["email"])

    canvas.setStrokeColor(line)
    canvas.setLineWidth(0.45)
    canvas.line(78 * mm, contact_y - 6 * mm, 78 * mm, contact_y + 6 * mm)
    canvas.line(139 * mm, contact_y - 6 * mm, 139 * mm, contact_y + 6 * mm)

    _draw_wave_footer(canvas, width, details)


def _draw_pdf_signature(
    canvas: pdf_canvas.Canvas,
    width: float,
    details: dict[str, str],
) -> None:
    orange = colors.HexColor(ORANGE)
    navy = colors.HexColor(NAVY)
    line = colors.HexColor(LINE)

    canvas.setFillColor(navy)
    canvas.setFont("Helvetica", 8.0)
    canvas.drawString(10 * mm, 99 * mm, details["closing_line_1"])
    canvas.drawString(10 * mm, 94 * mm, details["closing_line_2"])

    box_x = 10 * mm
    box_y = 69 * mm
    box_w = 99 * mm
    box_h = 21.5 * mm
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.8)
    canvas.roundRect(box_x, box_y, box_w, box_h, 2.5 * mm, stroke=1, fill=0)
    canvas.setStrokeColor(line)
    canvas.setLineWidth(0.55)
    canvas.line(box_x + 19 * mm, box_y + 4 * mm, box_x + 19 * mm, box_y + box_h - 4 * mm)

    canvas.setStrokeColor(orange)
    canvas.setLineWidth(1.4)
    canvas.line(box_x + 6.5 * mm, box_y + 7 * mm, box_x + 13 * mm, box_y + 13.5 * mm)
    canvas.line(box_x + 8.2 * mm, box_y + 5.8 * mm, box_x + 14.7 * mm, box_y + 12.3 * mm)
    canvas.line(box_x + 6.5 * mm, box_y + 7 * mm, box_x + 5.6 * mm, box_y + 4.6 * mm)

    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.setFont("Helvetica", 8.2)
    canvas.drawCentredString(box_x + 60 * mm, box_y + 9.5 * mm, details["signature_label"])

    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(10 * mm, 64 * mm, details["signer_name"])
    canvas.setFont("Helvetica", 7.3)
    canvas.drawString(10 * mm, 59.5 * mm, details["signer_title"])

    stamp_x = width - 33 * mm
    stamp_y = 78 * mm
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.8)
    canvas.circle(stamp_x, stamp_y, 18 * mm, stroke=1, fill=0)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.setFont("Helvetica", 8.2)
    words = details["stamp_label"].split()
    if len(words) > 1:
        canvas.drawCentredString(stamp_x, stamp_y + 2 * mm, words[0])
        canvas.drawCentredString(stamp_x, stamp_y - 3 * mm, " ".join(words[1:]))
    else:
        canvas.drawCentredString(stamp_x, stamp_y, details["stamp_label"])


def export_pdf(document: StudioDocument) -> bytes:
    source = export_base_pdf(_export_proxy(document))
    details = stationery_values(document.settings, document)
    reader = PdfReader(BytesIO(source))
    writer = PdfWriter()
    page_count = len(reader.pages)
    for index, page in enumerate(reader.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = pdf_canvas.Canvas(overlay_buffer, pagesize=(width, height))
        _draw_pdf_header_footer(overlay_canvas, width, height, details)
        if index == page_count - 1:
            _draw_pdf_signature(overlay_canvas, width, details)
        overlay_canvas.save()
        overlay_buffer.seek(0)
        page.merge_page(PdfReader(overlay_buffer).pages[0], over=True)
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata({key: str(value) for key, value in reader.metadata.items() if value is not None})
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _set_run(run: Any, *, size: float, bold: bool = False, color: str = NAVY) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))


def _cell_border(cell: Any, *, top: str | None = None, bottom: str | None = None, left: str | None = None, right: str | None = None, size: str = "6") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for side, color in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        if color is None:
            continue
        node = borders.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), color.lstrip("#"))


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
    _set_run(logo.add_run("G"), size=24, bold=True, color=ORANGE)

    brand = header.add_paragraph()
    brand.alignment = WD_ALIGN_PARAGRAPH.CENTER
    brand.paragraph_format.space_after = Pt(1)
    _set_run(brand.add_run("GUARDRISK"), size=19, bold=True, color=ORANGE)

    tagline = header.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tagline.paragraph_format.space_after = Pt(7)
    _set_run(tagline.add_run(f"—   {details['tagline'].upper()}   —"), size=6.7, color=NAVY)

    available = section.page_width - section.left_margin - section.right_margin
    meta = header.add_table(rows=1, cols=2, width=available)
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta.autofit = False
    left_cell, right_cell = meta.rows[0].cells
    left_cell.width = int(available * 0.5)
    right_cell.width = int(available * 0.5)
    right_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    _cell_border(right_cell, left=LINE, size="4")

    left_lines = (
        ("Date: ", details["date_time"]),
        ("To: ", details["recipient"]),
        ("Company: ", details["company"]),
    )
    left_paragraph = left_cell.paragraphs[0]
    left_paragraph.paragraph_format.space_after = Pt(0)
    for index, (label, value) in enumerate(left_lines):
        _set_run(left_paragraph.add_run(label), size=7.0, bold=True)
        _set_run(left_paragraph.add_run(value), size=7.0, color=MUTED)
        if index < len(left_lines) - 1:
            left_paragraph.add_run().add_break()

    address = right_cell.paragraphs[0]
    address.paragraph_format.left_indent = Mm(5)
    address.paragraph_format.space_after = Pt(0)
    _set_run(address.add_run("Address: "), size=7.0, bold=True)
    _set_run(address.add_run(details["address_line_1"]), size=7.0, color=MUTED)
    address.add_run().add_break()
    _set_run(address.add_run(" " * 11 + details["address_line_2"]), size=7.0, color=MUTED)
    address.add_run().add_break()
    _set_run(address.add_run(" " * 11 + details["address_line_3"]), size=7.0, color=MUTED)

    subject = header.add_table(rows=1, cols=1, width=available)
    subject.alignment = WD_TABLE_ALIGNMENT.CENTER
    subject_cell = subject.cell(0, 0)
    _cell_border(subject_cell, bottom=ORANGE, size="8")
    subject_paragraph = subject_cell.paragraphs[0]
    subject_paragraph.paragraph_format.space_before = Pt(6)
    subject_paragraph.paragraph_format.space_after = Pt(2)
    _set_run(subject_paragraph.add_run("RE: "), size=10.5, bold=True, color=ORANGE)
    _set_run(subject_paragraph.add_run(details["subject"]), size=10.5, bold=True, color=ORANGE)


def _add_docx_footer(section: Any, details: dict[str, str]) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    _clear_story(footer)
    available = section.page_width - section.left_margin - section.right_margin
    table = footer.add_table(rows=1, cols=3, width=available)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    values = (
        f"●  {details['address_line_1']}\n   {details['address_line_2']}\n   {details['address_line_3']}",
        f"●  {details['phone_1']}\n   {details['phone_2']}",
        f"●  {details['email']}",
    )
    for index, (cell, value) in enumerate(zip(table.rows[0].cells, values, strict=True)):
        if index:
            _cell_border(cell, left=LINE, size="4")
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        for line_index, line_value in enumerate(value.split("\n")):
            _set_run(paragraph.add_run(line_value), size=5.7, color=MUTED)
            if line_index < len(value.split("\n")) - 1:
                paragraph.add_run().add_break()

    labels = footer.add_paragraph()
    labels.paragraph_format.space_before = Pt(5)
    labels.paragraph_format.space_after = Pt(0)
    _set_run(labels.add_run(details["footer_left"].upper()), size=5.7, bold=True, color=ORANGE)
    labels.add_run(" " * 35)
    _set_run(labels.add_run(details["footer_right"].upper()), size=5.7, bold=True, color=ORANGE)


def _add_docx_signature(word: WordDocument, details: dict[str, str]) -> None:
    closing = word.add_paragraph()
    closing.paragraph_format.space_before = Pt(26)
    closing.paragraph_format.space_after = Pt(5)
    _set_run(closing.add_run(details["closing_line_1"]), size=8.5, color=NAVY)
    closing.add_run().add_break()
    _set_run(closing.add_run(details["closing_line_2"]), size=8.5, color=NAVY)

    outer = word.add_table(rows=1, cols=2)
    outer.alignment = WD_TABLE_ALIGNMENT.CENTER
    outer.autofit = False
    left, right = outer.rows[0].cells
    left.width = Mm(115)
    right.width = Mm(48)

    signature = left.add_table(rows=1, cols=2)
    signature.autofit = False
    pen, prompt = signature.rows[0].cells
    pen.width = Mm(24)
    prompt.width = Mm(76)
    _cell_border(pen, top=ORANGE, bottom=ORANGE, left=ORANGE, size="8")
    _cell_border(prompt, top=ORANGE, bottom=ORANGE, right=ORANGE, left=LINE, size="8")
    pen_paragraph = pen.paragraphs[0]
    pen_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run(pen_paragraph.add_run("✎"), size=18, color=ORANGE)
    prompt_paragraph = prompt.paragraphs[0]
    prompt_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run(prompt_paragraph.add_run(details["signature_label"]), size=8.0, color=MUTED)

    signer = left.add_paragraph()
    signer.paragraph_format.space_before = Pt(3)
    signer.paragraph_format.space_after = Pt(0)
    _set_run(signer.add_run(details["signer_name"]), size=8.0, bold=True, color=NAVY)
    signer.add_run().add_break()
    _set_run(signer.add_run(details["signer_title"]), size=7.7, color=NAVY)

    stamp = right.paragraphs[0]
    stamp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    stamp.paragraph_format.space_before = Pt(16)
    stamp.paragraph_format.space_after = Pt(16)
    _cell_border(right, top=ORANGE, bottom=ORANGE, left=ORANGE, right=ORANGE, size="8")
    for index, word_part in enumerate(details["stamp_label"].split()):
        _set_run(stamp.add_run(word_part), size=8.3, color=MUTED)
        if index < len(details["stamp_label"].split()) - 1:
            stamp.add_run().add_break()


def export_docx(document: StudioDocument) -> bytes:
    source = export_base_docx(_export_proxy(document))
    details = stationery_values(document.settings, document)
    word = WordDocument(BytesIO(source))
    for section in word.sections:
        section.top_margin = Mm(101)
        section.bottom_margin = Mm(55)
        section.left_margin = Mm(max(18.0, _number((document.settings or {}).get("margin_left_mm"), 20.0)))
        section.right_margin = Mm(max(18.0, _number((document.settings or {}).get("margin_right_mm"), 20.0)))
        section.header_distance = Mm(3)
        section.footer_distance = Mm(2)
        _add_docx_header(section, details)
        _add_docx_footer(section, details)

    _add_docx_signature(word, details)
    core = word.core_properties
    core.author = "Guardrisk Insurance Brokers"
    core.subject = "Official Guardrisk correspondence"
    core.comments = "Generated by gRisk Document Studio using the approved Guardrisk stationery"
    output = BytesIO()
    word.save(output)
    return output.getvalue()
