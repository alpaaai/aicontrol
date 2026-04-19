"""Tests for policy CRUD endpoints."""
import uuid
import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@contextmanager
def _auth_override(role: str = "admin"):
    from app.main import app
    from app.core.auth import _get_verified_token
    app.dependency_overrides[_get_verified_token] = lambda: {"role": role}
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_verified_token, None)


def _opa_patch():
    return patch(
        "app.services.policy_loader.push_rego_to_opa",
        new=AsyncMock(return_value=None)
    )


@pytest.mark.asyncio
async def test_list_policies_returns_200():
    from app.main import app
    with _auth_override("admin"), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/policies")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_policies_returns_list():
    from app.main import app
    with _auth_override("admin"), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/policies")
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_policy_returns_201():
    from app.main import app
    payload = {
        "name": f"test_policy_{uuid.uuid4().hex[:6]}",
        "rule_type": "tool_denylist",
        "condition": {"blocked_tools": ["bad_tool"]},
        "action": "deny",
        "severity": "high",
        "description": "Test policy",
        "compliance_frameworks": [],
    }
    with _auth_override("admin"), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/policies", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_policy_requires_admin():
    from app.main import app
    with _auth_override("agent"), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/policies", json={
                "name": "test", "rule_type": "default_allow",
                "condition": {}, "action": "allow",
                "severity": "low", "compliance_frameworks": [],
            })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_policy_returns_404_for_missing():
    from app.main import app
    with _auth_override("admin"), _opa_patch():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/policies/{uuid.uuid4()}")
    assert response.status_code == 404
