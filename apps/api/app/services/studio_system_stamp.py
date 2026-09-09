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
PALE = "#F6F8FB"
WHITE = "#FFFFFF"
MASERU_TZ = ZoneInfo("Africa/Maseru")


@dataclass(frozen=True)
class SystemStamp:
    brand: str
    legal_name: str
    status: str
    issuer: str
    issued_date: str
    reference: str
    content_hash: str


def _backend_now(value: datetime | None = None) -> datetime:
    instant = value or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(MASERU_TZ)


def build_system_stamp(document: Any, *, issued_at: datetime | None = None) -> SystemStamp:
    """Build immutable stamp data from the backend document and export time."""
    document_id = str(getattr(document, "id", "")).replace("-", "").upper()
    version = int(getattr(document, "version", 1) or 1)
    title = str(getattr(document, "title", ""))
    html_content = str(getattr(document, "html_content", ""))
    digest_source = f"{document_id}|{version}|{title}|{html_content}".encode()
    digest = sha256(digest_source).hexdigest()[:10].upper()
    reference_root = document_id[:8] or digest[:8]
    return SystemStamp(
        brand="GUARDRISK",
        legal_name="INSURANCE BROKERS",
        status="OFFICIAL",
        issuer="SYSTEM VERIFIED",
        issued_date=_backend_now(issued_at).strftime("%d %b %Y").upper(),
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
    """Draw the official stamp as vector artwork directly into the backend PDF."""
    stamp = build_system_stamp(document)
    radius = diameter / 2
    orange = colors.HexColor(ORANGE)
    navy = colors.HexColor(NAVY)
    muted = colors.HexColor(MUTED)
    pale = colors.HexColor(PALE)

    canvas.saveState()

    # Solid white face with a formal double-ring seal.
    canvas.setFillColor(colors.white)
    canvas.circle(center_x, center_y, radius, stroke=0, fill=1)
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(2.2)
    canvas.circle(center_x, center_y, radius - 1.4, stroke=1, fill=0)
    canvas.setStrokeColor(navy)
    canvas.setLineWidth(0.9)
    canvas.circle(center_x, center_y, radius - 5.4, stroke=1, fill=0)

    # Brand lockup.
    canvas.setFillColor(orange)
    canvas.setFont("Helvetica-Bold", 7.8)
    canvas.drawCentredString(center_x, center_y + radius * 0.53, stamp.brand)
    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 4.2)
    canvas.drawCentredString(center_x, center_y + radius * 0.39, stamp.legal_name)

    # Central official mark.
    mark_y = center_y + radius * 0.12
    mark_radius = radius * 0.16
    canvas.setFillColor(orange)
    canvas.circle(center_x, mark_y, mark_radius, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Bold", 10.5)
    canvas.drawCentredString(center_x, mark_y - 3.5, "G")

    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 9.3)
    canvas.drawCentredString(center_x, center_y - radius * 0.10, stamp.status)
    canvas.setFont("Helvetica-Bold", 4.6)
    canvas.drawCentredString(center_x, center_y - radius * 0.23, stamp.issuer)

    # A dedicated date band makes the backend issue date obvious and legible.
    band_width = radius * 1.20
    band_height = radius * 0.25
    band_x = center_x - band_width / 2
    band_y = center_y - radius * 0.48
    canvas.setFillColor(pale)
    canvas.setStrokeColor(orange)
    canvas.setLineWidth(0.6)
    canvas.roundRect(band_x, band_y, band_width, band_height, band_height / 2, stroke=1, fill=1)
    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 4.9)
    canvas.drawCentredString(center_x, band_y + band_height * 0.34, f"DATE  {stamp.issued_date}")

    # Traceability stays present but visually secondary.
    canvas.setFillColor(navy)
    canvas.setFont("Helvetica-Bold", 4.2)
    canvas.drawCentredString(center_x, center_y - radius * 0.66, stamp.reference)
    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 3.4)
    canvas.drawCentredString(center_x, center_y - radius * 0.79, f"VERIFY {stamp.content_hash}")

    # Small registration dots balance the seal without cluttering it.
    canvas.setFillColor(orange)
    dot_radius = max(0.9, radius * 0.03)
    canvas.circle(center_x - radius * 0.73, center_y, dot_radius, stroke=0, fill=1)
    canvas.circle(center_x + radius * 0.73, center_y, dot_radius, stroke=0, fill=1)
    canvas.restoreState()


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _centered(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text((center_x - width / 2, y), text, font=font, fill=fill)


def render_system_stamp_png(document: Any, *, size: int = 900) -> bytes:
    """Render the same official seal as a high-resolution backend PNG for DOCX."""
    stamp = build_system_stamp(document)
    image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)

    margin = int(size * 0.035)
    inner_margin = int(size * 0.095)
    stroke_outer = max(5, int(size * 0.012))
    stroke_inner = max(2, int(size * 0.0045))
    center = size / 2

    draw.ellipse(
        (margin, margin, size - margin, size - margin),
        fill=WHITE,
        outline=ORANGE,
        width=stroke_outer,
    )
    draw.ellipse(
        (inner_margin, inner_margin, size - inner_margin, size - inner_margin),
        outline=NAVY,
        width=stroke_inner,
    )

    _centered(draw, center, size * 0.145, stamp.brand, _font(int(size * 0.072)), ORANGE)
    _centered(draw, center, size * 0.225, stamp.legal_name, _font(int(size * 0.032)), NAVY)

    mark_radius = int(size * 0.075)
    mark_y = int(size * 0.385)
    draw.ellipse(
        (center - mark_radius, mark_y - mark_radius, center + mark_radius, mark_y + mark_radius),
        fill=ORANGE,
    )
    mark_font = _font(int(size * 0.085))
    mark_box = draw.textbbox((0, 0), "G", font=mark_font)
    mark_w = mark_box[2] - mark_box[0]
    mark_h = mark_box[3] - mark_box[1]
    draw.text(
        (center - mark_w / 2, mark_y - mark_h / 2 - mark_box[1]),
        "G",
        font=mark_font,
        fill=WHITE,
    )

    _centered(draw, center, size * 0.475, stamp.status, _font(int(size * 0.092)), NAVY)
    _centered(draw, center, size * 0.585, stamp.issuer, _font(int(size * 0.035)), NAVY)

    # Prominent professional date capsule.
    band_left = int(size * 0.225)
    band_top = int(size * 0.655)
    band_right = int(size * 0.775)
    band_bottom = int(size * 0.735)
    draw.rounded_rectangle(
        (band_left, band_top, band_right, band_bottom),
        radius=int(size * 0.04),
        fill=PALE,
        outline=ORANGE,
        width=max(2, int(size * 0.0035)),
    )
    date_font = _font(int(size * 0.036))
    date_text = f"DATE  {stamp.issued_date}"
    date_box = draw.textbbox((0, 0), date_text, font=date_font)
    date_w = date_box[2] - date_box[0]
    date_h = date_box[3] - date_box[1]
    draw.text(
        (center - date_w / 2, (band_top + band_bottom - date_h) / 2 - date_box[1]),
        date_text,
        font=date_font,
        fill=NAVY,
    )

    _centered(draw, center, size * 0.765, stamp.reference, _font(int(size * 0.031)), NAVY)
    _centered(draw, center, size * 0.815, f"VERIFY {stamp.content_hash}", _font(int(size * 0.024)), MUTED)

    dot = max(5, int(size * 0.012))
    draw.ellipse((size * 0.125 - dot, center - dot, size * 0.125 + dot, center + dot), fill=ORANGE)
    draw.ellipse((size * 0.875 - dot, center - dot, size * 0.875 + dot, center + dot), fill=ORANGE)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
