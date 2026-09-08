import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.identity import Role, User


@pytest.mark.asyncio
async def test_superuser_administration_lifecycle_and_staff_denial() -> None:
    password = "Testing-Only-Strong-Password-42"
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    staff_email = f"staff-{uuid.uuid4().hex}@example.com"

    async with AsyncSessionLocal() as session:
        broker_role = await session.scalar(select(Role).where(Role.name == "broker"))
        assert broker_role is not None
        admin = User(
            email=admin_email,
            full_name="Administration Test Superuser",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        staff = User(
            email=staff_email,
            full_name="Administration Test Staff",
            password_hash=hash_password(password),
            is_active=True,
            is_superuser=False,
            roles=[broker_role],
        )
        session.add_all([admin, staff])
        await session.flush()
        admin_id = admin.id
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_email, "password": password},
        )
        assert admin_login.status_code == 200
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        roles = await client.get("/api/v1/admin/roles", headers=admin_headers)
        assert roles.status_code == 200
        role_names = {role["name"] for role in roles.json()}
        assert {"broker", "claims", "finance", "medical", "risk"}.issubset(role_names)

        created_email = f"created-{uuid.uuid4().hex}@example.com"
        created_password = "Created-User-Password-42"
        created = await client.post(
            "/api/v1/admin/users",
            headers=admin_headers,
            json={
                "email": created_email,
                "full_name": "Created Admin Test User",
                "password": created_password,
                "role_names": ["claims"],
                "is_active": True,
                "is_superuser": False,
            },
        )
        assert created.status_code == 201
        created_payload = created.json()
        created_id = created_payload["id"]
        assert created_payload["roles"] == ["claims"]

        updated = await client.patch(
            f"/api/v1/admin/users/{created_id}",
            headers=admin_headers,
            json={"full_name": "Updated Admin Test User", "role_names": ["broker", "claims"]},
        )
        assert updated.status_code == 200
        assert updated.json()["full_name"] == "Updated Admin Test User"
        assert updated.json()["roles"] == ["broker", "claims"]

        self_deactivate = await client.patch(
            f"/api/v1/admin/users/{admin_id}",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert self_deactivate.status_code == 409

        replacement_password = "Replacement-Password-For-Test-42"
        reset = await client.post(
            f"/api/v1/admin/users/{created_id}/reset-password",
            headers=admin_headers,
            json={"password": replacement_password},
        )
        assert reset.status_code == 204

        replacement_login = await client.post(
            "/api/v1/auth/login",
            data={"username": created_email, "password": replacement_password},
        )
        assert replacement_login.status_code == 200

        audit = await client.get(
            "/api/v1/admin/audit?page=1&page_size=100&q=admin",
            headers=admin_headers,
        )
        assert audit.status_code == 200
        audit_actions = {item["action"] for item in audit.json()["items"]}
        assert "admin.user_created" in audit_actions
        assert "admin.user_updated" in audit_actions
        assert "admin.password_reset" in audit_actions

        staff_login = await client.post(
            "/api/v1/auth/login",
            data={"username": staff_email, "password": password},
        )
        assert staff_login.status_code == 200
        staff_headers = {"Authorization": f"Bearer {staff_login.json()['access_token']}"}
        denied = await client.get("/api/v1/admin/users", headers=staff_headers)
        assert denied.status_code == 403
