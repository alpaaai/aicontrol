"""Writes immutable audit events for every intercepted tool call."""
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AuditEvent


async def write_event(
    session: AsyncSession,
    session_id: uuid.UUID,
    agent_id: uuid.UUID,
    agent_name: str,
    tool_name: str,
    tool_parameters: dict[str, Any],
    decision: str,
    decision_reason: str,
    sequence_number: int,
    duration_ms: int,
    policy_id: Optional[uuid.UUID] = None,
    policy_name: Optional[str] = None,
    tool_response: Optional[dict] = None,
    risk_delta: int = 0,
) -> uuid.UUID:
    """Persist one audit event. Returns the new event's UUID."""
    event_id = uuid.uuid4()
    event = AuditEvent(
        id=event_id,
        session_id=session_id,
        agent_id=agent_id,
        agent_name=agent_name,
        tool_name=tool_name,
        tool_parameters=tool_parameters,
        tool_response=tool_response,
        policy_id=policy_id,
        policy_name=policy_name,
        decision=decision,
        decision_reason=decision_reason,
        sequence_number=sequence_number,
        duration_ms=duration_ms,
        risk_delta=risk_delta,
    )
    session.add(event)
    await session.flush()
    return event_id
