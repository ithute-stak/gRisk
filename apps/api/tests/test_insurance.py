import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.customer import Customer
from app.models.identity import User


@pytest.mark.asyncio
async def test_insurance_quote_to_policy_lifecycle() -> None:
    password = "Testing-Only-Strong-Password-42"
    email = f"insurance-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            email=email,
            full_name="Insurance Test User",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        customer = Customer(
            customer_type="company",
            display_name="SC Construction Test",
            company_name="SC Construction Test",
            email="sc-test@example.com",
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

        product_response = await client.post(
            "/api/v1/insurance/products",
            headers=headers,
            json={
                "code": f"CAR-{uuid.uuid4().hex[:8]}",
                "name": "Contractors All Risk",
                "category": "general-insurance",
                "description": "Construction works and third party liability cover.",
            },
        )
        assert product_response.status_code == 201
        product_id = product_response.json()["id"]

        quote_response = await client.post(
            "/api/v1/insurance/quotes",
            headers=headers,
            json={
                "customer_id": str(customer_id),
                "product_id": product_id,
                "currency": "LSL",
                "sum_insured": "2250000.00",
                "premium": "8610.00",
                "third_party_limit": "1000000.00",
                "start_date": "2026-09-10",
                "end_date": "2026-12-10",
                "notes": "Construction of classrooms and latrines.",
                "items": [
                    {"label": "Contract works", "amount": "2250000.00"},
                    {"label": "Third party liability", "amount": "1000000.00"},
                ],
            },
        )
        assert quote_response.status_code == 201
        quote = quote_response.json()
        assert quote["quote_number"].startswith("Q-")
        assert quote["status"] == "draft"
        assert len(quote["items"]) == 2

        premature_policy_response = await client.post(
            f"/api/v1/insurance/quotes/{quote['id']}/convert-to-policy",
            headers=headers,
            json={"start_date": "2026-09-10", "end_date": "2026-12-10"},
        )
        assert premature_policy_response.status_code == 409

        for quote_status in ("review", "submitted", "accepted"):
            status_response = await client.patch(
                f"/api/v1/insurance/quotes/{quote['id']}/status",
                headers=headers,
                json={"status": quote_status},
            )
            assert status_response.status_code == 200
            assert status_response.json()["status"] == quote_status

            if quote_status != "accepted":
                blocked_policy_response = await client.post(
                    f"/api/v1/insurance/quotes/{quote['id']}/convert-to-policy",
                    headers=headers,
                    json={"start_date": "2026-09-10", "end_date": "2026-12-10"},
                )
                assert blocked_policy_response.status_code == 409

        policy_response = await client.post(
            f"/api/v1/insurance/quotes/{quote['id']}/convert-to-policy",
            headers=headers,
            json={"start_date": "2026-09-10", "end_date": "2026-12-10"},
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        assert policy["policy_number"].startswith("P-")
        assert policy["source_quote_id"] == quote["id"]
        assert policy["premium"] == "8610.00"

        duplicate_policy_response = await client.post(
            f"/api/v1/insurance/quotes/{quote['id']}/convert-to-policy",
            headers=headers,
            json={"start_date": "2026-09-10", "end_date": "2026-12-10"},
        )
        assert duplicate_policy_response.status_code == 409

        policies_response = await client.get(
            "/api/v1/insurance/policies",
            headers=headers,
            params={"customer_id": str(customer_id)},
        )
        assert policies_response.status_code == 200
        assert any(item["id"] == policy["id"] for item in policies_response.json())
