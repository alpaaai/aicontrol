"""Tests that routers are mounted and startup runs."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_intercept_route_exists():
    """POST /intercept route must be registered on the app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/intercept" in routes


@pytest.mark.asyncio
async def test_health_still_works():
    """GET /health must still return 200 after router changes."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
