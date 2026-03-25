import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UUID, Boolean, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="unregistered")
    framework: Mapped[Optional[str]] = mapped_column(String(50))
    model_version: Mapped[Optional[str]] = mapped_column(String(100))
    system_prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    approved_tools: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, server_default="{}")
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())

    sessions: Mapped[list["Session"]] = relationship(back_populates="agent")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="agent")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    trigger_context: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(String(20), server_default="active")
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, server_default="{}")
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    agent: Mapped[Optional["Agent"]] = relationship(back_populates="sessions")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="session")
    hitl_reviews: Mapped[list["HITLReview"]] = relationship(back_populates="session")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    applies_to_agents: Mapped[Optional[list]] = mapped_column(JSONB, server_default="[]")
    compliance_frameworks: Mapped[Optional[list]] = mapped_column(JSONB, server_default="[]")
    severity: Mapped[Optional[str]] = mapped_column(String(20), server_default="medium")
    active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default="true")
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())

    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="policy")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    agent_name: Mapped[Optional[str]] = mapped_column(String(100))
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_parameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    tool_response: Mapped[Optional[dict]] = mapped_column(JSONB)
    policy_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"))
    policy_name: Mapped[Optional[str]] = mapped_column(String(100))
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text)
    risk_delta: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())

    session: Mapped[Optional["Session"]] = relationship(back_populates="audit_events")
    agent: Mapped[Optional["Agent"]] = relationship(back_populates="audit_events")
    policy: Mapped[Optional["Policy"]] = relationship(back_populates="audit_events")
    hitl_review: Mapped[Optional["HITLReview"]] = relationship(back_populates="audit_event")


class HITLReview(Base):
    __tablename__ = "hitl_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("audit_events.id"))
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100))
    notified_via: Mapped[Optional[str]] = mapped_column(String(50))
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    response_deadline: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    reviewer: Mapped[Optional[str]] = mapped_column(String(100))
    review_note: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())

    audit_event: Mapped[Optional["AuditEvent"]] = relationship(back_populates="hitl_review")
    session: Mapped[Optional["Session"]] = relationship(back_populates="hitl_reviews")
