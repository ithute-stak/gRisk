import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_login_rate_limit_blocks_repeated_failures() -> None:
    email = f"missing-{uuid.uuid4().hex}@example.com"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": "wrong-password"},
            )
            assert response.status_code == 401

        blocked = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "wrong-password"},
        )
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == "Too many login attempts. Try again later."
