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


from contextlib import contextmanager

@contextmanager
def _mock_auth():
    from app.main import app
    from app.core.auth import require_agent
    app.dependency_overrides[require_agent] = lambda: {"role": "agent"}
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_agent, None)


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
    )), _mock_auth():
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
    )), _mock_auth():
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
    )), _mock_auth():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    data = response.json()
    assert "audit_event_id" in data
    assert data["audit_event_id"] == str(event_id)


@pytest.mark.asyncio
async def test_intercept_requires_auth():
    """POST /intercept without token must return 403."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/intercept", json=make_payload())
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_intercept_fires_hitl_on_review_decision():
    """POST /intercept must call create_hitl_review when decision is review."""
    from app.main import app

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "review", "reason": "requires_human_review"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=uuid.uuid4()
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )), patch(
        "app.routers.intercept.create_hitl_review",
        new=AsyncMock(return_value=uuid.uuid4())
    ) as mock_hitl, patch(
        "app.routers.intercept.post_slack_review",
        new=AsyncMock(return_value="ts")
    ), _mock_auth():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    assert mock_hitl.called
