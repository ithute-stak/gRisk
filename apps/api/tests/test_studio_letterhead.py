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
    stationery_values,
)

CUSTOM_ADDRESS = "LNDC Centre, Ground Floor, Shop No. 12"
CUSTOM_DATE = "09 September 2026, 11:16"
CUSTOM_RECIPIENT = "Mpho Mosotho"
CUSTOM_COMPANY = "Example Company"
CUSTOM_SUBJECT = "Medical Aid Confirmation"
CUSTOM_TAGLINE = "Your Link to Premier Healthcare"
DOCUMENT_ID = uuid.UUID("12345678-1234-5678-1234-56781234abcd")


def _document() -> StudioDocument:
    html = """
    <h1>Official correspondence</h1>
    <p>First page body content.</p>
    <div data-page-break="true"></div>
    <p>Second page body content.</p>
    """
    return StudioDocument(
        id=DOCUMENT_ID,
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
            "letterhead_date_time": CUSTOM_DATE,
            "letterhead_code": "GRK-LEGACY",
            "letterhead_recipient": CUSTOM_RECIPIENT,
            "letterhead_company": CUSTOM_COMPANY,
            "letterhead_address": CUSTOM_ADDRESS,
            "letterhead_subject": CUSTOM_SUBJECT,
            "letterhead_tagline": CUSTOM_TAGLINE,
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


def test_official_settings_remove_legacy_code_and_keep_editable_details() -> None:
    document = _document()
    settings = official_settings(document.settings, document)
    assert settings["brand_header"] is True
    assert settings["official_letterhead"] == "guardrisk_editable_v5_no_code"
    assert "letterhead_code" not in settings
    assert settings["letterhead_date_time"] == CUSTOM_DATE
    assert settings["letterhead_recipient"] == CUSTOM_RECIPIENT
    assert settings["letterhead_company"] == CUSTOM_COMPANY
    assert settings["letterhead_subject"] == CUSTOM_SUBJECT
    assert settings["letterhead_tagline"] == CUSTOM_TAGLINE
    assert settings["letterhead_address"] == CUSTOM_ADDRESS
    assert settings["letterhead_phone_1"] == "+266 2232 2537"
    assert settings["letterhead_phone_2"] == "+266 6272 0488"


def test_stationery_values_have_no_code_field() -> None:
    document = _document()
    details = stationery_values(document.settings, document)
    assert "code" not in details
    assert details["date_time"] == CUSTOM_DATE


def test_pdf_repeats_custom_editable_stationery_without_code() -> None:
    payload = export_pdf(_document())
    assert payload.startswith(b"%PDF")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) >= 2

    for page in reader.pages:
        text = page.extract_text() or ""
        assert "GUARDRISK" in text
        assert "DOCUMENT STUDIO" not in text
        assert "Code:" not in text
        assert "GRK-" not in text
        assert CUSTOM_TAGLINE.upper() in text
        assert CUSTOM_DATE in text
        assert CUSTOM_RECIPIENT in text
        assert CUSTOM_COMPANY in text
        assert CUSTOM_SUBJECT in text
        assert CUSTOM_ADDRESS in text
        assert "+266 2232 2537" in text
        assert "+266 6272 0488" in text
        assert "custom@guardrisk.co.ls" in text
        assert "GUARDRISK HEALTH" in text
        assert "LOW COST MEDICAL AID" in text

    complete_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "First page body content." in complete_text
    assert "Second page body content." in complete_text


def test_docx_uses_custom_template_fields_without_code() -> None:
    payload = export_docx(_document())
    assert payload.startswith(b"PK")
    word = WordDocument(BytesIO(payload))
    assert word.sections

    for section in word.sections:
        header_text = _container_text(section.header)
        footer_text = _container_text(section.footer)
        assert "GUARDRISK" in header_text
        assert "DOCUMENT STUDIO" not in header_text
        assert "Code:" not in header_text
        assert "GRK-" not in header_text
        assert CUSTOM_TAGLINE.upper() in header_text
        assert CUSTOM_DATE in header_text
        assert CUSTOM_RECIPIENT in header_text
        assert CUSTOM_COMPANY in header_text
        assert CUSTOM_SUBJECT in header_text
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
