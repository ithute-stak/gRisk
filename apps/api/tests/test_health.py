import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_and_health_endpoints() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        root_response = await client.get("/api/v1")
        assert root_response.status_code == 200
        root_payload = root_response.json()
        assert root_payload["name"] == "gRisk API"
        assert root_payload["version"] == "1.0.0"
        assert root_response.headers["x-content-type-options"] == "nosniff"
        assert root_response.headers["x-frame-options"] == "DENY"
        assert root_response.headers["cache-control"] == "no-store"
        assert len(root_response.headers["x-request-id"]) == 32

        health_response = await client.get("/api/v1/health")
        assert health_response.status_code == 200
        health_payload = health_response.json()
        assert health_payload["status"] == "ok"
        assert health_payload["services"] == {
            "api": True,
            "postgres": True,
            "redis": True,
        }

        live_response = await client.get("/api/v1/health/live")
        assert live_response.status_code == 200
        assert live_response.json() == {"status": "ok", "service": "api"}

        ready_response = await client.get("/api/v1/health/ready")
        assert ready_response.status_code == 200
        assert ready_response.json()["status"] == "ok"
