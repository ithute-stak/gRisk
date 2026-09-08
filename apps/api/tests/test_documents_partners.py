import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.identity import Role, User


@pytest.mark.asyncio
async def test_document_upload_download_archive_and_partner_lifecycle() -> None:
    password = "Testing-Only-Strong-Password-42"
    email = f"operations-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        broker_role = await session.scalar(select(Role).where(Role.name == "broker"))
        assert broker_role is not None
        user = User(
            email=email,
            full_name="Documents Partners Test User",
            password_hash=hash_password(password),
            is_active=True,
            roles=[broker_role],
        )
        customer = Customer(
            customer_type="company",
            display_name="Document Test Customer",
            company_name="Document Test Customer",
            status="active",
        )
        session.add_all([user, customer])
        await session.commit()
        customer_id = customer.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        pdf_bytes = b"%PDF-1.4\n% gRisk test document\n%%EOF\n"
        uploaded = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={
                "customer_id": str(customer_id),
                "category": "policy",
                "entity_type": "policy",
                "entity_id": "POL-TEST-001",
                "description": "Policy schedule test",
            },
            files={"file": ("policy-schedule.pdf", pdf_bytes, "application/pdf")},
        )
        assert uploaded.status_code == 201
        document = uploaded.json()
        document_id = document["id"]
        assert document["filename"] == "policy-schedule.pdf"
        assert document["customer_id"] == str(customer_id)
        assert document["size_bytes"] == len(pdf_bytes)

        listed = await client.get(
            f"/api/v1/documents?customer_id={customer_id}&category=policy",
            headers=headers,
        )
        assert listed.status_code == 200
        assert listed.json()["total"] == 1

        downloaded = await client.get(
            f"/api/v1/documents/{document_id}/download",
            headers=headers,
        )
        assert downloaded.status_code == 200
        assert downloaded.content == pdf_bytes
        assert "policy-schedule.pdf" in downloaded.headers["content-disposition"]

        archived = await client.patch(
            f"/api/v1/documents/{document_id}/archive",
            headers=headers,
            json={},
        )
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"

        active_after_archive = await client.get(
            f"/api/v1/documents?customer_id={customer_id}",
            headers=headers,
        )
        assert active_after_archive.status_code == 200
        assert active_after_archive.json()["total"] == 0

        partner_name = f"Test Insurer {uuid.uuid4().hex[:8]}"
        partner = await client.post(
            "/api/v1/partners",
            headers=headers,
            json={
                "partner_type": "insurer",
                "name": partner_name,
                "email": "test-insurer@example.com",
                "integration_status": "not_configured",
                "notes": "Awaiting confirmed provider API details",
                "is_active": True,
            },
        )
        assert partner.status_code == 201
        partner_payload = partner.json()
        assert partner_payload["partner_number"].startswith("PAR-")
        assert partner_payload["integration_status"] == "not_configured"

        updated_partner = await client.patch(
            f"/api/v1/partners/{partner_payload['id']}",
            headers=headers,
            json={"integration_status": "sandbox", "external_reference": "SANDBOX-01"},
        )
        assert updated_partner.status_code == 200
        assert updated_partner.json()["integration_status"] == "sandbox"
        assert updated_partner.json()["external_reference"] == "SANDBOX-01"

        partners = await client.get(
            "/api/v1/partners?partner_type=insurer&integration_status=sandbox",
            headers=headers,
        )
        assert partners.status_code == 200
        assert any(item["id"] == partner_payload["id"] for item in partners.json()["items"])
