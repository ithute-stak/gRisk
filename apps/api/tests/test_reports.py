import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.identity import User


@pytest.mark.asyncio
async def test_management_reporting_endpoints() -> None:
    password = "Reporting-Testing-Only-Password-42"
    email = f"reports-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="Reporting Test User",
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

        executive = await client.get("/api/v1/reports/executive", headers=headers)
        assert executive.status_code == 200
        executive_payload = executive.json()
        assert executive_payload["customers"] >= 0
        assert executive_payload["active_policies"] >= 0
        assert executive_payload["outstanding_balance"].count(".") == 1
        assert len(executive_payload["outstanding_balance"].split(".")[1]) == 2

        portfolio = await client.get("/api/v1/reports/portfolio", headers=headers)
        assert portfolio.status_code == 200
        assert "policies_by_status" in portfolio.json()
        assert "risk_items_by_level" in portfolio.json()

        finance = await client.get("/api/v1/reports/finance", headers=headers)
        assert finance.status_code == 200
        assert finance.json()["payments"] >= 0
        assert finance.json()["outstanding_balance"].count(".") == 1

        claims = await client.get("/api/v1/reports/claims", headers=headers)
        assert claims.status_code == 200
        assert claims.json()["general_claims"] >= 0
        assert claims.json()["medical_claims"] >= 0
