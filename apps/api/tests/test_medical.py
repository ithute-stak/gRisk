import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.identity import User


@pytest.mark.asyncio
async def test_medical_aid_member_benefit_and_claim_lifecycle() -> None:
    password = "Testing-Only-Strong-Password-42"
    email = f"medical-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="Medical Aid Test User",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        customer = Customer(
            customer_type="individual",
            display_name="Medical Test Member",
            first_name="Medical",
            last_name="Member",
            email=f"member-{uuid.uuid4().hex}@example.com",
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

        plan_response = await client.post(
            "/api/v1/medical/plans",
            headers=headers,
            json={
                "code": f"SAVER-{uuid.uuid4().hex[:8]}",
                "name": "Basic Saver Test",
                "description": "Configurable low-cost medical aid test plan.",
                "currency": "LSL",
            },
        )
        assert plan_response.status_code == 201
        plan_id = plan_response.json()["id"]

        gp_response = await client.post(
            f"/api/v1/medical/plans/{plan_id}/benefits",
            headers=headers,
            json={
                "code": "GP",
                "name": "General Practitioner",
                "category": "outpatient",
                "annual_monetary_limit": "1000.00",
                "per_event_limit": "400.00",
                "annual_visit_limit": 5,
            },
        )
        assert gp_response.status_code == 201
        gp_id = gp_response.json()["id"]

        specialist_response = await client.post(
            f"/api/v1/medical/plans/{plan_id}/benefits",
            headers=headers,
            json={
                "code": "SPECIALIST",
                "name": "Specialist Consultation",
                "category": "specialist",
                "annual_monetary_limit": "2000.00",
                "requires_authorisation": True,
            },
        )
        assert specialist_response.status_code == 201
        specialist_id = specialist_response.json()["id"]

        member_response = await client.post(
            "/api/v1/medical/members",
            headers=headers,
            json={
                "customer_id": str(customer_id),
                "plan_id": plan_id,
                "start_date": "2026-01-01",
                "status": "active",
            },
        )
        assert member_response.status_code == 201
        member = member_response.json()
        assert member["member_number"].startswith("MED-")
        member_id = member["id"]

        dependant_response = await client.post(
            f"/api/v1/medical/members/{member_id}/dependants",
            headers=headers,
            json={
                "first_name": "Child",
                "last_name": "Member",
                "relationship_type": "child",
                "date_of_birth": "2015-06-01",
            },
        )
        assert dependant_response.status_code == 201
        dependant_id = dependant_response.json()["id"]

        before_balance = await client.get(
            f"/api/v1/medical/members/{member_id}/benefits/{gp_id}/balance",
            headers=headers,
            params={"year": 2026},
        )
        assert before_balance.status_code == 200
        assert before_balance.json()["remaining_amount"] == "1000.00"
        assert before_balance.json()["remaining_units"] == 5

        utilisation_response = await client.post(
            "/api/v1/medical/utilisations",
            headers=headers,
            json={
                "member_id": member_id,
                "benefit_id": gp_id,
                "dependant_id": dependant_id,
                "service_date": "2026-09-08",
                "amount": "200.00",
                "units": 1,
                "provider_name": "Test Medical Centre",
            },
        )
        assert utilisation_response.status_code == 201

        after_balance = await client.get(
            f"/api/v1/medical/members/{member_id}/benefits/{gp_id}/balance",
            headers=headers,
            params={"year": 2026},
        )
        assert after_balance.status_code == 200
        assert after_balance.json()["used_amount"] == "200.00"
        assert after_balance.json()["remaining_amount"] == "800.00"
        assert after_balance.json()["used_units"] == 1
        assert after_balance.json()["remaining_units"] == 4

        unauthorised_specialist = await client.post(
            "/api/v1/medical/utilisations",
            headers=headers,
            json={
                "member_id": member_id,
                "benefit_id": specialist_id,
                "service_date": "2026-09-08",
                "amount": "500.00",
                "units": 1,
            },
        )
        assert unauthorised_specialist.status_code == 409

        auth_response = await client.post(
            "/api/v1/medical/authorisations",
            headers=headers,
            json={
                "member_id": member_id,
                "benefit_id": specialist_id,
                "requested_amount": "500.00",
                "provider_name": "Specialist Clinic",
            },
        )
        assert auth_response.status_code == 201
        authorisation_id = auth_response.json()["id"]

        decision_response = await client.patch(
            f"/api/v1/medical/authorisations/{authorisation_id}",
            headers=headers,
            json={"status": "approved", "approved_amount": "500.00"},
        )
        assert decision_response.status_code == 200
        assert decision_response.json()["status"] == "approved"

        authorised_specialist = await client.post(
            "/api/v1/medical/utilisations",
            headers=headers,
            json={
                "member_id": member_id,
                "benefit_id": specialist_id,
                "service_date": "2026-09-08",
                "amount": "500.00",
                "units": 1,
            },
        )
        assert authorised_specialist.status_code == 201

        cash_claim_response = await client.post(
            "/api/v1/medical/claims",
            headers=headers,
            json={
                "member_id": member_id,
                "claim_kind": "cash_plan",
                "service_date": "2026-09-01",
                "admission_date": "2026-09-01",
                "discharge_date": "2026-09-05",
                "claim_amount": "1200.00",
                "provider_name": "Test Hospital",
                "description": "Hospital cash-plan claim for workflow testing.",
            },
        )
        assert cash_claim_response.status_code == 201
        claim = cash_claim_response.json()
        assert claim["claim_number"].startswith("MCL-")
        assert claim["status"] == "submitted"

        review_response = await client.patch(
            f"/api/v1/medical/claims/{claim['id']}/status",
            headers=headers,
            json={"status": "review"},
        )
        assert review_response.status_code == 200

        approved_response = await client.patch(
            f"/api/v1/medical/claims/{claim['id']}/status",
            headers=headers,
            json={"status": "approved", "approved_amount": "1000.00"},
        )
        assert approved_response.status_code == 200
        assert approved_response.json()["approved_amount"] == "1000.00"

        paid_response = await client.patch(
            f"/api/v1/medical/claims/{claim['id']}/status",
            headers=headers,
            json={"status": "paid"},
        )
        assert paid_response.status_code == 200

        listed = await client.get("/api/v1/medical/claims", headers=headers)
        assert listed.status_code == 200
        assert any(item["id"] == claim["id"] for item in listed.json())
