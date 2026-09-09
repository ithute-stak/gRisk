import uuid
from datetime import datetime, timezone
from io import BytesIO

from PIL import Image

from app.models.studio import StudioDocument
from app.services.studio_system_stamp import build_system_stamp, render_system_stamp_png


def _document() -> StudioDocument:
    return StudioDocument(
        id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        owner_user_id=uuid.uuid4(),
        title="Professional Stamp Test",
        template_key="formal_letter",
        style_key="guardrisk_orange",
        content_json={"type": "doc", "content": []},
        html_content="<p>Official content</p>",
        plain_text="Official content",
        settings={},
        version=7,
    )


def test_stamp_uses_backend_export_date_and_traceable_reference() -> None:
    stamp = build_system_stamp(
        _document(),
        issued_at=datetime(2026, 9, 9, 22, 30, tzinfo=timezone.utc),
    )
    # 22:30 UTC is already 10 September in Maseru (UTC+02:00).
    assert stamp.issued_date == "10 SEP 2026"
    assert stamp.brand == "GUARDRISK"
    assert stamp.legal_name == "INSURANCE BROKERS"
    assert stamp.status == "OFFICIAL"
    assert stamp.issuer == "SYSTEM VERIFIED"
    assert stamp.reference == "GR-AAAAAAAA-V7"
    assert len(stamp.content_hash) == 10


def test_stamp_png_is_high_resolution_square_artwork() -> None:
    payload = render_system_stamp_png(_document())
    image = Image.open(BytesIO(payload))
    assert image.format == "PNG"
    assert image.size == (900, 900)
    assert image.mode == "RGBA"
