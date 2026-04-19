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
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
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
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
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
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
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
    ), patch("app.routers.intercept.ensure_session", new=AsyncMock(
    )), _mock_auth():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    assert mock_hitl.called


@pytest.mark.asyncio
async def test_allow_decision_persists_parameters():
    """Allow decisions must pass tool_parameters to write_event."""
    from app.main import app
    captured = {}

    async def capture_write_event(**kwargs):
        captured.update(kwargs)
        return uuid.uuid4()

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "allow", "reason": "default_allow"}
    )), patch(
        "app.routers.intercept.write_event", new=AsyncMock(side_effect=capture_write_event)
    ), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
    )), _mock_auth():
        payload = {
            "session_id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "agent_name": "test-agent",
            "tool_name": "query_inventory_system",
            "tool_parameters": {"warehouse_id": "WH-001", "sku": "COMP-MCU-32"},
            "sequence_number": 1,
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=payload)

    assert response.status_code == 200
    assert response.json()["decision"] == "allow"
    assert captured.get("tool_parameters") == {"warehouse_id": "WH-001", "sku": "COMP-MCU-32"}


@pytest.mark.asyncio
async def test_http_tool_captures_domain():
    """HTTP tool calls must have domain extracted into tool_parameters before write."""
    from app.main import app
    captured = {}

    async def capture_write_event(**kwargs):
        captured.update(kwargs)
        return uuid.uuid4()

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "deny", "reason": "tool_blacklisted"}
    )), patch(
        "app.routers.intercept.write_event", new=AsyncMock(side_effect=capture_write_event)
    ), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
    )), _mock_auth():
        payload = {
            "session_id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "agent_name": "supplier-agent",
            "tool_name": "http_post",
            "tool_parameters": {
                "url": "https://api.supplier-network-exchange.com/orders",
                "body": {"sku": "COMP-MCU-32"},
            },
            "sequence_number": 3,
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=payload)

    assert response.status_code == 200
    params = captured.get("tool_parameters", {})
    assert params.get("domain") == "api.supplier-network-exchange.com"


@pytest.mark.asyncio
async def test_deny_writes_policy_name():
    """Deny decisions must pass policy_name to write_event when a matching policy exists."""
    from app.main import app
    captured = {}
    policy_id = uuid.uuid4()

    async def capture_write_event(**kwargs):
        captured.update(kwargs)
        return uuid.uuid4()

    policies = [
        {
            "id": str(policy_id),
            "name": "block_dangerous_tool",
            "rule_type": "tool_denylist",
            "action": "deny",
            "severity": "critical",
            "condition": {"blocked_tools": ["dangerous_tool"]},
        }
    ]

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "deny", "reason": "tool_blacklisted"}
    )), patch(
        "app.routers.intercept.write_event", new=AsyncMock(side_effect=capture_write_event)
    ), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=policies
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
    )), _mock_auth():
        payload = {
            "session_id": str(uuid.uuid4()),
            "agent_id": str(uuid.uuid4()),
            "agent_name": "test-agent",
            "tool_name": "dangerous_tool",
            "tool_parameters": {},
            "sequence_number": 1,
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=payload)

    assert response.status_code == 200
    assert captured.get("policy_name") == "block_dangerous_tool"


@pytest.mark.asyncio
async def test_intercept_returns_review_id_on_review_decision():
    """POST /intercept must return review_id when decision is review."""
    from app.main import app
    event_id = uuid.uuid4()
    review_id = uuid.uuid4()

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "review", "reason": "requires_human_review"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=event_id
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )), patch("app.routers.intercept.create_hitl_review", new=AsyncMock(
        return_value=review_id
    )), patch("app.routers.intercept.post_slack_review", new=AsyncMock(
        return_value="ts"
    )), patch("app.routers.intercept.ensure_session", new=AsyncMock(
    )), _mock_auth():
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    data = response.json()
    assert "review_id" in data
    assert data["review_id"] == str(review_id)


@pytest.mark.asyncio
async def test_ensure_session_creates_when_missing():
    """ensure_session must insert a Session row when session_id is not found."""
    from app.routers.intercept import ensure_session
    from app.models.schemas import Session

    session_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    await ensure_session(mock_db, session_id, agent_id)

    mock_db.add.assert_called_once()
    added = mock_db.add.call_args[0][0]
    assert isinstance(added, Session)
    assert added.id == session_id
    assert added.agent_id == agent_id
    assert added.status == "active"
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_session_noop_when_exists():
    """ensure_session must not insert when session already exists."""
    from app.routers.intercept import ensure_session

    session_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()  # row found
    mock_db.execute.return_value = mock_result

    await ensure_session(mock_db, session_id, agent_id)

    mock_db.add.assert_not_called()
    mock_db.flush.assert_not_called()
