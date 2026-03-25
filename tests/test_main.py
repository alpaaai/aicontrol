"""Tests for FastAPI app and /health endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_returns_200():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_json_status_ok():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_includes_service_name():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    data = response.json()
    assert "service" in data
    assert data["service"] == "aicontrol"
