from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas

ORANGE = "#F23808"
NAVY = "#17345F"
MUTED = "#4B617F"
WHITE = "#FFFFFF"


@dataclass(frozen=True)
class SystemStamp:
    brand: str
    status: str
    issuer: str
    issued_date: str
    reference: str
    content_hash: str


def _document_timestamp(document: Any) -> datetime:
    value = getattr(document, "updated_at", None) or getattr(document, "created_at", None)
    if not isinstance(value, datetime):
        value = datetime.now(timezone.utc)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo("Africa/Maseru"))


def build_system_stamp(document: Any) -> SystemStamp:
    document_id = str(getattr(document, "id", "")).replace("-", "").upper()
    version = int(getattr(document, "version", 1) or 1)
    title = str(getattr(document, "title", ""))
    html_content = str(getattr(document, "html_content", ""))
    digest_source = f"{document_id}|{version}|{title}|{html_content}".encode()
    digest = sha256(digest_source).hexdigest()[:10].upper()
    reference_root = document_id[:8] or digest[:8]
    return SystemStamp(
        brand="GUARDRISK",
        status="OFFICIAL",
        issuer="SYSTEM GENERATED",
        issued_date=_document_timestamp(document).strftime("%d %b %Y").upper(),
        reference=f"GR-{reference_root}-V{version}",
        content_hash=digest,
    )


def draw_pdf_system_stamp(
    canvas: pdf_canvas.Canvas,
    document: Any,
    *,
    center_x: float,
    center_y: float,
    diameter: float,
) -> None:
    stamp = build_system_stamp(document)
    radius = diameter / 2
    orange = colors.HexColor(ORANGE)
    navy = colors.HexColor(NAVY)
    muted = colors.HexColor(MUTED)

    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.circle(center_x, center_y, radius, stroke=0, fill=1)

    canvas.setStrokeColor(orange)
    canvas.setLineWidth(1.8)
    canvas.circle(center_x, center_y, radius - 1.2, stroke=1, fill=0)
    canvas.setStrokeColor(navy)
    canvas.setLineWidth(0.8)
    canvas.circle(center_x, center_y, radius - 5.2, stroke=1, fill=0)

    canvas.setFillColor(orange)
    canvas.setFont("Helvetica-Bold", 8.2)
    canvas.drawCentredString(center_x, center_y + radius * 0.47, stamp.brand)

    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.55)
    canvas.line(center_x - radius * 0.58, center_y + radius * 0.26, center_x + radius * 0.58, center_y + radius * 0.26)
    canvas.line(center_x - radius * 0.58, center_y - radius * 0.10, center_x + radius * 0.58, center_y - radius * 0.10)

    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 10.3)
    canvas.drawCentredString(center_x, center_y + radius * 0.04, stamp.status)
    canvas.setFont("Helvetica-Bold", 6.0)
    canvas.drawCentredString(center_x, center_y - radius * 0.28, stamp.issuer)

    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 5.2)
    canvas.drawCentredString(center_x, center_y - radius * 0.48, stamp.issued_date)
    canvas.setFont("Helvetica-Bold", 4.7)
    canvas.drawCentredString(center_x, center_y - radius * 0.64, stamp.reference)
    canvas.setFont("Helvetica", 3.9)
    canvas.drawCentredString(center_x, center_y - radius * 0.77, f"HASH {stamp.content_hash}")

    canvas.setFillColor(orange)
    dot_radius = max(1.0, radius * 0.035)
    canvas.circle(center_x - radius * 0.72, center_y, dot_radius, stroke=0, fill=1)
    canvas.circle(center_x + radius * 0.72, center_y, dot_radius, stroke=0, fill=1)
    canvas.restoreState()


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _centered(draw: ImageDraw.ImageDraw, center_x: float, y: float, text: str, font: ImageFont.ImageFont, fill: str) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text((center_x - width / 2, y), text, font=font, fill=fill)


def render_system_stamp_png(document: Any, *, size: int = 720) -> bytes:
    stamp = build_system_stamp(document)
    image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.035)
    inner_margin = int(size * 0.095)
    stroke_outer = max(4, int(size * 0.012))
    stroke_inner = max(2, int(size * 0.005))

    draw.ellipse((margin, margin, size - margin, size - margin), fill=WHITE, outline=ORANGE, width=stroke_outer)
    draw.ellipse(
        (inner_margin, inner_margin, size - inner_margin, size - inner_margin),
        outline=NAVY,
        width=stroke_inner,
    )

    center = size / 2
    _centered(draw, center, size * 0.17, stamp.brand, _font(int(size * 0.075)), ORANGE)
    line_left = size * 0.23
    line_right = size * 0.77
    draw.line((line_left, size * 0.36, line_right, size * 0.36), fill=ORANGE, width=max(2, int(size * 0.004)))
    draw.line((line_left, size * 0.56, line_right, size * 0.56), fill=ORANGE, width=max(2, int(size * 0.004)))

    _centered(draw, center, size * 0.395, stamp.status, _font(int(size * 0.105)), NAVY)
    _centered(draw, center, size * 0.585, stamp.issuer, _font(int(size * 0.048)), NAVY)
    _centered(draw, center, size * 0.675, stamp.issued_date, _font(int(size * 0.043)), MUTED)
    _centered(draw, center, size * 0.745, stamp.reference, _font(int(size * 0.038)), NAVY)
    _centered(draw, center, size * 0.805, f"HASH {stamp.content_hash}", _font(int(size * 0.029)), MUTED)

    dot = max(5, int(size * 0.014))
    draw.ellipse((size * 0.125 - dot, center - dot, size * 0.125 + dot, center + dot), fill=ORANGE)
    draw.ellipse((size * 0.875 - dot, center - dot, size * 0.875 + dot, center + dot), fill=ORANGE)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
