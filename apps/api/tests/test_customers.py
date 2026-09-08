import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit import AuditEvent
from app.models.identity import User


@pytest.mark.asyncio
async def test_authenticated_customer_lifecycle_and_audit() -> None:
    password = "Testing-Only-Strong-Password-42"
    email = f"crm-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="CRM Test User",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = await client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "customer_type": "company",
                "company_name": "Maseru Construction Group",
                "registration_number": "TEST-REG-001",
                "email": "office@example.com",
                "phone": "+266 2232 0000",
                "status": "active",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        customer_id = created["id"]
        assert created["display_name"] == "Maseru Construction Group"
        assert created["customer_number"].startswith("GR-")
        assert created["contacts"] == []
        assert created["addresses"] == []
        assert created["notes"] == []

        list_response = await client.get(
            "/api/v1/customers",
            headers=headers,
            params={"q": "Maseru Construction", "page": 1, "page_size": 10},
        )
        assert list_response.status_code == 200
        listed = list_response.json()
        assert listed["total"] == 1
        assert listed["items"][0]["id"] == customer_id

        contact_response = await client.post(
            f"/api/v1/customers/{customer_id}/contacts",
            headers=headers,
            json={
                "name": "Thabo Mokoena",
                "role": "Finance Manager",
                "email": "thabo@example.com",
                "phone": "+266 5800 0000",
            },
        )
        assert contact_response.status_code == 201

        address_response = await client.post(
            f"/api/v1/customers/{customer_id}/addresses",
            headers=headers,
            json={
                "address_type": "physical",
                "line1": "Kingsway Road",
                "city": "Maseru",
                "district": "Maseru",
                "country": "Lesotho",
            },
        )
        assert address_response.status_code == 201

        note_response = await client.post(
            f"/api/v1/customers/{customer_id}/notes",
            headers=headers,
            json={"body": "Initial corporate onboarding completed."},
        )
        assert note_response.status_code == 201

        update_response = await client.patch(
            f"/api/v1/customers/{customer_id}",
            headers=headers,
            json={"status": "prospect", "phone": "+266 2232 1111"},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["status"] == "prospect"
        assert updated["phone"] == "+266 2232 1111"
        assert len(updated["contacts"]) == 1
        assert len(updated["addresses"]) == 1
        assert len(updated["notes"]) == 1

    async with AsyncSessionLocal() as session:
        audit_count = await session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.entity_type == "customer",
                AuditEvent.entity_id == customer_id,
            )
        )
        assert (audit_count or 0) >= 5
