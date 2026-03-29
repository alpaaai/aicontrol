"""Tests for agent CRUD endpoints."""
import uuid
import pytest
from contextlib import contextmanager
from httpx import AsyncClient, ASGITransport


@contextmanager
def _auth(role: str = "admin"):
    from app.main import app
    from app.core.auth import _get_verified_token
    app.dependency_overrides[_get_verified_token] = lambda: {"role": role}
    try:
        yield app
    finally:
        app.dependency_overrides.pop(_get_verified_token, None)


@pytest.mark.asyncio
async def test_list_agents_returns_200():
    with _auth() as app:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/agents")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_agents_returns_list():
    with _auth() as app:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/agents")
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_agent_returns_201():
    payload = {
        "name": f"test-agent-{uuid.uuid4().hex[:6]}",
        "owner": "test@example.com",
        "framework": "langchain",
        "model_version": "gpt-4o",
    }
    with _auth() as app:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/agents", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_agent_requires_admin():
    with _auth(role="agent") as app:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/agents", json={
                "name": "test", "owner": "test@example.com"
            })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_agent_returns_404_for_missing():
    with _auth() as app:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/agents/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_agent_returns_404_for_missing():
    with _auth() as app:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/agents/{uuid.uuid4()}")
    assert response.status_code == 404
