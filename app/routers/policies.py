"""Policy CRUD endpoints — admin only."""
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.models.database import get_db
from app.models.schemas import Policy
from app.services.policy_loader import push_rego_to_opa

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    condition: dict[str, Any]
    action: str
    severity: str = "medium"
    compliance_frameworks: list[str] = []


class PolicyUpdate(BaseModel):
    description: Optional[str] = None
    condition: Optional[dict[str, Any]] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    active: Optional[bool] = None
    compliance_frameworks: Optional[list[str]] = None


class PolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    rule_type: str
    condition: dict[str, Any]
    action: str
    severity: Optional[str]
    active: Optional[bool]
    compliance_frameworks: Optional[list]

    class Config:
        from_attributes = True


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> list[PolicyResponse]:
    result = await db.execute(select(Policy).order_by(Policy.name))
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> PolicyResponse:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> PolicyResponse:
    policy = Policy(
        name=body.name,
        description=body.description,
        rule_type=body.rule_type,
        condition=body.condition,
        action=body.action,
        severity=body.severity,
        compliance_frameworks=body.compliance_frameworks,
        active=True,
    )
    db.add(policy)
    await db.flush()
    await push_rego_to_opa()
    return policy


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> PolicyResponse:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(policy, field, value)
    await db.flush()
    await push_rego_to_opa()
    return policy


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_admin),
) -> None:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(policy)
    await push_rego_to_opa()
