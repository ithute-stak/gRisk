import uuid
from io import BytesIO

from docx import Document as WordDocument
from pypdf import PdfReader

from app.models.studio import StudioDocument
from app.services.studio_letterhead import export_docx, export_pdf, official_settings


def _document() -> StudioDocument:
    html = """
    <h1>Official correspondence</h1>
    <p>First page body content.</p>
    <div data-page-break="true"></div>
    <p>Second page body content.</p>
    """
    return StudioDocument(
        id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        title="Letterhead Test",
        template_key="formal_letter",
        style_key="classic_word",
        content_json={"type": "doc", "content": []},
        html_content=html,
        plain_text="Official correspondence First page body content. Second page body content.",
        settings={
            "page_size": "a4",
            "orientation": "portrait",
            "margin_top_mm": 12,
            "margin_right_mm": 12,
            "margin_bottom_mm": 12,
            "margin_left_mm": 12,
            "brand_header": False,
        },
        version=4,
    )


def _header_footer_text(container) -> str:
    return "\n".join(paragraph.text for paragraph in container.paragraphs)


def test_official_settings_lock_stationery_on() -> None:
    settings = official_settings({"brand_header": False})
    assert settings["brand_header"] is True
    assert settings["official_letterhead"] == "guardrisk_minimal_v3"


def test_pdf_repeats_compact_letterhead_and_footer_on_every_page() -> None:
    payload = export_pdf(_document())
    assert payload.startswith(b"%PDF")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) >= 2

    for page in reader.pages:
        text = page.extract_text() or ""
        assert "GUARDRISK" in text
        assert "INSURANCE BROKERS" in text
        assert "Guardrisk Insurance Brokers" in text
        assert "LNDC Centre, Kingsway, Maseru 100" in text
        assert "info@guardrisk.co.ls" in text
        assert "+266 2232 2537 / 6272 0488" in text
        assert "REFERENCE" not in text

    complete_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "First page body content." in complete_text
    assert "Second page body content." in complete_text


def test_docx_uses_compact_stationery_even_when_legacy_branding_is_off() -> None:
    payload = export_docx(_document())
    assert payload.startswith(b"PK")
    word = WordDocument(BytesIO(payload))
    assert word.sections

    for section in word.sections:
        header_text = _header_footer_text(section.header)
        footer_text = _header_footer_text(section.footer)
        assert "GUARDRISK" in header_text
        assert "INSURANCE BROKERS" in header_text
        assert "DATE" not in header_text
        assert "REFERENCE" not in header_text
        assert "OFFICIAL CORRESPONDENCE" not in header_text
        assert "Guardrisk Insurance Brokers" in footer_text
        assert "LNDC Centre, Kingsway, Maseru 100" in footer_text
        assert "info@guardrisk.co.ls" in footer_text
        assert "+266 2232 2537 / 6272 0488" in footer_text

    body_text = "\n".join(paragraph.text for paragraph in word.paragraphs)
    assert "First page body content." in body_text
    assert "Second page body content." in body_text
