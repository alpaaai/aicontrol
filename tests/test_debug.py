"""Tests for /debug endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_debug_returns_200():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/debug")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_debug_returns_required_fields():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/debug")
    data = response.json()
    for field in ["version", "database", "opa", "policies", "agents", "last_event"]:
        assert field in data, f"/debug missing field: {field}"


@pytest.mark.asyncio
async def test_debug_is_public():
    """GET /debug must not require a token."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/debug")
    assert response.status_code not in (401, 403)
