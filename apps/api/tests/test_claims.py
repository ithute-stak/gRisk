import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.identity import User
from app.models.insurance import InsuranceProduct, Policy


@pytest.mark.asyncio
async def test_claim_registration_and_workflow() -> None:
    password = "Testing-Only-Strong-Password-42"
    email = f"claims-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="Claims Test User",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        customer = Customer(
            customer_type="company",
            display_name="Claims Test Company",
            company_name="Claims Test Company",
            status="active",
        )
        product = InsuranceProduct(
            code=f"CLAIMS-{uuid.uuid4().hex[:8].upper()}",
            name="Claims Test Cover",
            category="General Insurance",
            is_active=True,
        )
        session.add_all([user, customer, product])
        await session.flush()
        policy = Policy(
            customer_id=customer.id,
            product_id=product.id,
            status="active",
            currency="LSL",
            sum_insured=Decimal("100000.00"),
            premium=Decimal("2500.00"),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        session.add(policy)
        await session.commit()
        policy_id = policy.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        outside_cover = await client.post(
            "/api/v1/claims",
            headers=headers,
            json={
                "policy_id": str(policy_id),
                "claim_type": "property",
                "incident_date": "2027-01-01",
                "description": "Incident outside the cover period.",
                "claim_amount": "5000.00",
                "priority": "normal",
            },
        )
        assert outside_cover.status_code == 409

        create_response = await client.post(
            "/api/v1/claims",
            headers=headers,
            json={
                "policy_id": str(policy_id),
                "claim_type": "property",
                "incident_date": "2026-08-20",
                "description": "Storm damage to insured business property.",
                "claim_amount": "5000.00",
                "priority": "high",
            },
        )
        assert create_response.status_code == 201
        claim = create_response.json()
        claim_id = claim["id"]
        assert claim["claim_number"].startswith("CLM-")
        assert claim["status"] == "reported"
        assert claim["priority"] == "high"
        assert claim["claim_amount"] == "5000.00"
        assert len(claim["events"]) == 1

        invalid_transition = await client.patch(
            f"/api/v1/claims/{claim_id}/status",
            headers=headers,
            json={"status": "approved", "approved_amount": "4500.00"},
        )
        assert invalid_transition.status_code == 409

        for next_status in ("triage", "assessment"):
            response = await client.patch(
                f"/api/v1/claims/{claim_id}/status",
                headers=headers,
                json={"status": next_status, "note": f"Moved to {next_status}."},
            )
            assert response.status_code == 200
            assert response.json()["status"] == next_status

        missing_approved_amount = await client.patch(
            f"/api/v1/claims/{claim_id}/status",
            headers=headers,
            json={"status": "approved"},
        )
        assert missing_approved_amount.status_code == 422

        excessive_approved_amount = await client.patch(
            f"/api/v1/claims/{claim_id}/status",
            headers=headers,
            json={"status": "approved", "approved_amount": "6000.00"},
        )
        assert excessive_approved_amount.status_code == 422

        approval = await client.patch(
            f"/api/v1/claims/{claim_id}/status",
            headers=headers,
            json={
                "status": "approved",
                "approved_amount": "4500.00",
                "note": "Assessment approved subject to settlement.",
            },
        )
        assert approval.status_code == 200
        assert approval.json()["approved_amount"] == "4500.00"

        note_response = await client.post(
            f"/api/v1/claims/{claim_id}/notes",
            headers=headers,
            json={"note": "Settlement documents received."},
        )
        assert note_response.status_code == 201
        assert note_response.json()["event_type"] == "claim.note_added"

        for next_status in ("settled", "closed"):
            response = await client.patch(
                f"/api/v1/claims/{claim_id}/status",
                headers=headers,
                json={"status": next_status, "note": f"Claim {next_status}."},
            )
            assert response.status_code == 200
            assert response.json()["status"] == next_status

        detail = await client.get(f"/api/v1/claims/{claim_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["status"] == "closed"
        assert len(detail.json()["events"]) >= 6

        claims = await client.get(
            "/api/v1/claims",
            headers=headers,
            params={"claim_status": "closed", "q": claim["claim_number"]},
        )
        assert claims.status_code == 200
        assert claims.json()["total"] == 1
        assert claims.json()["items"][0]["id"] == claim_id
