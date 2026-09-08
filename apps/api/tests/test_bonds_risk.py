import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.identity import User


@pytest.mark.asyncio
async def test_guarantee_and_risk_lifecycles() -> None:
    password = "Testing-Only-Strong-Password-42"
    email = f"risk-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="Bonds Risk Test User",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        customer = Customer(
            customer_type="company",
            display_name="Contractor Risk Test",
            company_name="Contractor Risk Test",
            email=f"contractor-{uuid.uuid4().hex}@example.com",
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

        guarantee_response = await client.post(
            "/api/v1/guarantees",
            headers=headers,
            json={
                "customer_id": str(customer_id),
                "guarantee_type": "performance_bond_guarantee",
                "beneficiary": "Ministry Test Beneficiary",
                "contract_reference": "TEST-CONTRACT-001",
                "contract_description": "Construction contract performance guarantee test.",
                "currency": "LSL",
                "contract_value": "2250000.00",
                "guarantee_amount": "225000.00",
                "issuer_name": "Test Insurer",
                "effective_date": "2026-09-10",
                "expiry_date": "2027-03-10",
            },
        )
        assert guarantee_response.status_code == 201
        guarantee = guarantee_response.json()
        assert guarantee["guarantee_number"].startswith("GRT-")
        assert guarantee["status"] == "draft"

        for next_status in ["review", "submitted", "approved", "issued", "released", "closed"]:
            status_response = await client.patch(
                f"/api/v1/guarantees/{guarantee['id']}/status",
                headers=headers,
                json={"status": next_status, "note": f"Move to {next_status}."},
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == next_status

        listed_guarantees = await client.get(
            "/api/v1/guarantees",
            headers=headers,
            params={"customer_id": str(customer_id)},
        )
        assert listed_guarantees.status_code == 200
        assert any(item["id"] == guarantee["id"] for item in listed_guarantees.json()["items"])

        assessment_response = await client.post(
            "/api/v1/risk/assessments",
            headers=headers,
            json={
                "customer_id": str(customer_id),
                "assessment_type": "enterprise_risk_management",
                "title": "Contractor enterprise risk assessment",
                "assessment_date": "2026-09-08",
                "summary": "Test assessment for the Guardrisk risk register workflow.",
            },
        )
        assert assessment_response.status_code == 201
        assessment = assessment_response.json()
        assert assessment["assessment_number"].startswith("RSK-")
        assert assessment["status"] == "draft"

        critical_item_response = await client.post(
            f"/api/v1/risk/assessments/{assessment['id']}/items",
            headers=headers,
            json={
                "category": "Operational",
                "title": "Major project delivery failure",
                "description": "Critical project execution risk.",
                "likelihood": 5,
                "impact": 4,
                "existing_controls": "Project supervision and progress reporting.",
                "treatment_plan": "Strengthen milestone controls and escalation.",
                "risk_owner": "Project Manager",
            },
        )
        assert critical_item_response.status_code == 201
        critical_item = critical_item_response.json()
        assert critical_item["inherent_score"] == 20
        assert critical_item["inherent_level"] == "critical"

        residual_item_response = await client.post(
            f"/api/v1/risk/assessments/{assessment['id']}/items",
            headers=headers,
            json={
                "category": "Financial",
                "title": "Cash-flow pressure",
                "likelihood": 4,
                "impact": 4,
                "existing_controls": "Monthly cash-flow forecasts.",
                "treatment_plan": "Maintain liquidity buffer and funding facilities.",
                "residual_likelihood": 2,
                "residual_impact": 3,
            },
        )
        assert residual_item_response.status_code == 201
        assert residual_item_response.json()["inherent_level"] == "high"
        assert residual_item_response.json()["residual_score"] == 6
        assert residual_item_response.json()["residual_level"] == "moderate"

        detail_response = await client.get(
            f"/api/v1/risk/assessments/{assessment['id']}",
            headers=headers,
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["overall_level"] == "critical"
        assert len(detail_response.json()["items"]) == 2

        dashboard_response = await client.get("/api/v1/risk/dashboard", headers=headers)
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        assert dashboard["assessments"] >= 1
        assert dashboard["open_items"] >= 2
        assert dashboard["high_or_critical_items"] >= 1

        for next_status in ["in_progress", "review", "completed"]:
            status_response = await client.patch(
                f"/api/v1/risk/assessments/{assessment['id']}/status",
                headers=headers,
                json={"status": next_status},
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == next_status

        archive_response = await client.patch(
            f"/api/v1/risk/assessments/{assessment['id']}/status",
            headers=headers,
            json={"status": "archived"},
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"
