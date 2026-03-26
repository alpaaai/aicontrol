"""POST /intercept — core tool call intercept endpoint."""
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import Policy
from app.services.opa_client import evaluate
from app.services.audit_writer import write_event

router = APIRouter()


class InterceptRequest(BaseModel):
    session_id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    tool_name: str
    tool_parameters: dict[str, Any] = {}
    sequence_number: int


class InterceptResponse(BaseModel):
    decision: str
    reason: str
    audit_event_id: uuid.UUID


async def get_active_policies(session: AsyncSession) -> list[dict]:
    """Load all active policies from Postgres as plain dicts for OPA."""
    result = await session.execute(
        select(Policy).where(Policy.active == True)
    )
    policies = result.scalars().all()
    return [
        {
            "name": p.name,
            "rule_type": p.rule_type,
            "condition": p.condition,
            "action": p.action,
            "severity": p.severity,
        }
        for p in policies
    ]


@router.post("/intercept", response_model=InterceptResponse)
async def intercept(
    request: InterceptRequest,
    db: AsyncSession = Depends(get_db),
) -> InterceptResponse:
    """
    Intercept a tool call, evaluate against policies, write audit event.
    Returns allow | deny | review plus the audit event ID.
    """
    start = time.monotonic()

    # Load active policies from DB
    policies = await get_active_policies(db)

    # Evaluate via OPA
    opa_result = await evaluate(
        tool_name=request.tool_name,
        tool_parameters=request.tool_parameters,
        policies=policies,
    )

    duration_ms = int((time.monotonic() - start) * 1000)

    # Write immutable audit event
    event_id = await write_event(
        session=db,
        session_id=request.session_id,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        tool_name=request.tool_name,
        tool_parameters=request.tool_parameters,
        decision=opa_result["decision"],
        decision_reason=opa_result["reason"],
        sequence_number=request.sequence_number,
        duration_ms=duration_ms,
    )

    return InterceptResponse(
        decision=opa_result["decision"],
        reason=opa_result["reason"],
        audit_event_id=event_id,
    )
