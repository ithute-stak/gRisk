import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.identity import Role, User


@pytest.mark.asyncio
async def test_viewer_is_read_only_and_module_writes_require_matching_role() -> None:
    password = "Testing-Only-Strong-Password-42"
    viewer_email = f"viewer-{uuid.uuid4().hex}@example.com"
    claims_email = f"claims-{uuid.uuid4().hex}@example.com"
    broker_email = f"broker-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        roles = {
            role.name: role
            for role in (
                await session.execute(select(Role).where(Role.name.in_(["viewer", "claims", "broker"])))
            ).scalars().all()
        }
        assert set(roles) == {"viewer", "claims", "broker"}
        session.add_all(
            [
                User(
                    email=viewer_email,
                    full_name="Viewer RBAC Test",
                    password_hash=hash_password(password),
                    is_active=True,
                    roles=[roles["viewer"]],
                ),
                User(
                    email=claims_email,
                    full_name="Claims RBAC Test",
                    password_hash=hash_password(password),
                    is_active=True,
                    roles=[roles["claims"]],
                ),
                User(
                    email=broker_email,
                    full_name="Broker RBAC Test",
                    password_hash=hash_password(password),
                    is_active=True,
                    roles=[roles["broker"]],
                ),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async def auth_headers(email: str) -> dict[str, str]:
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": password},
            )
            assert response.status_code == 200
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        viewer_headers = await auth_headers(viewer_email)
        claims_headers = await auth_headers(claims_email)
        broker_headers = await auth_headers(broker_email)

        viewer_read = await client.get("/api/v1/customers", headers=viewer_headers)
        assert viewer_read.status_code == 200

        viewer_write = await client.post(
            "/api/v1/customers",
            headers=viewer_headers,
            json={"customer_type": "company", "company_name": "Viewer Must Not Create"},
        )
        assert viewer_write.status_code == 403
        assert viewer_write.json()["detail"] == "Viewer accounts have read-only access"

        claims_read = await client.get("/api/v1/customers", headers=claims_headers)
        assert claims_read.status_code == 200

        claims_customer_write = await client.post(
            "/api/v1/customers",
            headers=claims_headers,
            json={"customer_type": "company", "company_name": "Claims Must Not Create Customer"},
        )
        assert claims_customer_write.status_code == 403
        assert claims_customer_write.json()["detail"] == "Your role does not permit this operational change"

        broker_customer_write = await client.post(
            "/api/v1/customers",
            headers=broker_headers,
            json={"customer_type": "company", "company_name": "Broker Customer Creation Test"},
        )
        assert broker_customer_write.status_code == 201
