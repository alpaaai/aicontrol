"""Tests for POST /intercept endpoint."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


def make_payload(tool_name="safe_tool"):
    return {
        "session_id": str(uuid.uuid4()),
        "agent_id": str(uuid.uuid4()),
        "agent_name": "test-agent",
        "tool_name": tool_name,
        "tool_parameters": {"key": "value"},
        "sequence_number": 1,
    }


@pytest.mark.asyncio
async def test_intercept_returns_200():
    """POST /intercept must return HTTP 200."""
    from app.main import app

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "allow", "reason": "default_allow"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=uuid.uuid4()
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_intercept_returns_decision():
    """POST /intercept response must include decision field."""
    from app.main import app

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "deny", "reason": "tool_blacklisted"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=uuid.uuid4()
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload("execute_code"))

    data = response.json()
    assert "decision" in data
    assert data["decision"] == "deny"


@pytest.mark.asyncio
async def test_intercept_returns_audit_event_id():
    """POST /intercept response must include audit_event_id."""
    from app.main import app
    event_id = uuid.uuid4()

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "allow", "reason": "default_allow"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=event_id
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    data = response.json()
    assert "audit_event_id" in data
    assert data["audit_event_id"] == str(event_id)
