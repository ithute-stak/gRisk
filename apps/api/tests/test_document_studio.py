import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.identity import User


@pytest.mark.asyncio
async def test_document_studio_renders_fillable_signature_pdf() -> None:
    password = "Document-Studio-Test-Password-42"
    email = f"document-studio-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="Document Studio Test User",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = await client.post(
            "/api/v1/document-studio/render",
            headers=headers,
            json={
                "document_title": "Formal Correspondence",
                "recipient_name": "The Managing Director",
                "recipient_company": "Demo Client (Pty) Ltd",
                "recipient_address": "Maseru 100\nLesotho",
                "recipient_phone": "+266 2231 0000",
                "recipient_email": "director@example.com",
                "reference": "GRISK/TEST/001",
                "document_date": "08 September 2026",
                "subject": "Document Studio Demo Letter",
                "body": (
                    "Dear Sir/Madam,\n\n"
                    "This is a generated executive letterhead PDF with a digital signature field."
                ),
                "signatory_name": "Authorised Signatory",
                "signatory_title": "Guardrisk Insurance Brokers",
                "signatory_contact": "+266 2232 2537 | info@guardrisk.co.ls",
                "include_signature_field": True,
                "include_document_stamp": True,
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert "document-studio-demo-letter.pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")
        assert len(response.content) > 3000

        reader = PdfReader(BytesIO(response.content))
        fields = reader.get_fields()
        assert fields is not None
        assert "signature" in fields
        assert fields["signature"]["/FT"] == "/Sig"
        assert reader.metadata is not None
        assert reader.metadata.creator == "gRisk Document Studio"
        assert reader.metadata.author == "Guardrisk Insurance Brokers"
