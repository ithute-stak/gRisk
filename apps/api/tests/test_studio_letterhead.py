import uuid
from io import BytesIO

from docx import Document as WordDocument
from pypdf import PdfReader

from app.models.studio import StudioDocument
from app.services.studio_letterhead import (
    export_docx,
    export_pdf,
    normalize_lesotho_phone,
    official_settings,
)

CUSTOM_ADDRESS = "LNDC Centre, Ground Floor, Shop No. 12"


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
            "letterhead_address": CUSTOM_ADDRESS,
            "letterhead_phone_1": "22322537",
            "letterhead_phone_2": "062720488",
            "letterhead_email": "custom@guardrisk.co.ls",
            "letterhead_footer_left": "Guardrisk Health",
            "letterhead_footer_right": "Low Cost Medical Aid",
        },
        version=4,
    )


def _container_text(container) -> str:
    paragraphs = [paragraph.text for paragraph in container.paragraphs]
    tables = [cell.text for table in container.tables for row in table.rows for cell in row.cells]
    return "\n".join([*paragraphs, *tables])


def test_phone_normalization_always_adds_lesotho_country_code() -> None:
    assert normalize_lesotho_phone("22322537") == "+266 2232 2537"
    assert normalize_lesotho_phone("062720488") == "+266 6272 0488"
    assert normalize_lesotho_phone("+266 5939 5332") == "+266 5939 5332"


def test_official_settings_lock_stationery_on_and_seed_editable_details() -> None:
    settings = official_settings({"brand_header": False})
    assert settings["brand_header"] is True
    assert settings["official_letterhead"] == "guardrisk_sketch_v3"
    assert settings["letterhead_address"].startswith("LNDC Centre, Ground Floor")
    assert settings["letterhead_phone_1"].startswith("+266")
    assert settings["letterhead_phone_2"].startswith("+266")


def test_pdf_repeats_custom_stationery_on_every_page() -> None:
    payload = export_pdf(_document())
    assert payload.startswith(b"%PDF")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) >= 2

    for page in reader.pages:
        text = page.extract_text() or ""
        assert "GUARDRISK" in text
        assert "D O C U M E N T" in text
        assert "YOUR LINK TO PREMIER HEALTHCARE" in text
        assert CUSTOM_ADDRESS in text
        assert "+266 2232 2537" in text
        assert "+266 6272 0488" in text
        assert "custom@guardrisk.co.ls" in text
        assert "GUARDRISK HEALTH" in text
        assert "LOW COST MEDICAL AID" in text

    complete_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "First page body content." in complete_text
    assert "Second page body content." in complete_text


def test_docx_uses_custom_stationery_and_normalized_numbers() -> None:
    payload = export_docx(_document())
    assert payload.startswith(b"PK")
    word = WordDocument(BytesIO(payload))
    assert word.sections

    for section in word.sections:
        header_text = _container_text(section.header)
        footer_text = _container_text(section.footer)
        assert "GUARDRISK" in header_text
        assert "D O C U M E N T" in header_text
        assert "YOUR LINK TO PREMIER HEALTHCARE" in header_text
        assert CUSTOM_ADDRESS in header_text
        assert CUSTOM_ADDRESS in footer_text
        assert "+266 2232 2537" in footer_text
        assert "+266 6272 0488" in footer_text
        assert "custom@guardrisk.co.ls" in footer_text
        assert "GUARDRISK HEALTH" in footer_text
        assert "LOW COST MEDICAL AID" in footer_text

    body_text = "\n".join(paragraph.text for paragraph in word.paragraphs)
    assert "First page body content." in body_text
    assert "Second page body content." in body_text
