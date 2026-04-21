"""Tests for audit writer — event persistence."""
import uuid
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_write_event_calls_session_add():
    """write_event must add an AuditEvent to the session."""
    from app.services.audit_writer import write_event

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.flush = AsyncMock()

    event_id = await write_event(
        session=mock_session,
        session_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        agent_name="test-agent",
        tool_name="safe_tool",
        tool_parameters={"key": "value"},
        decision="allow",
        decision_reason="default_allow",
        sequence_number=1,
        duration_ms=42,
    )

    assert mock_session.add.called
    assert event_id is not None


@pytest.mark.asyncio
async def test_write_event_returns_uuid():
    """write_event must return a UUID for the created event."""
    from app.services.audit_writer import write_event

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.flush = AsyncMock()

    event_id = await write_event(
        session=mock_session,
        session_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        agent_name="test-agent",
        tool_name="safe_tool",
        tool_parameters={},
        decision="deny",
        decision_reason="tool_denylisted",
        sequence_number=2,
        duration_ms=10,
    )

    assert isinstance(event_id, uuid.UUID)
