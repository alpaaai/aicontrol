"""All dashboard DB query functions. Return plain dicts, never ORM objects."""
from typing import Any

from sqlalchemy import text

from dashboard.db import get_sync_session


def get_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent audit events for the log view."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT
                ae.id,
                ae.tool_name,
                ae.decision,
                ae.decision_reason,
                ae.agent_name,
                ae.sequence_number,
                ae.duration_ms,
                ae.risk_delta,
                ae.created_at,
                p.name AS policy_name
            FROM audit_events ae
            LEFT JOIN policies p ON ae.policy_id = p.id
            ORDER BY ae.created_at DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def get_policies() -> list[dict[str, Any]]:
    """Return all active policies."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT id, name, description, rule_type, action,
                   severity, active, created_at
            FROM policies
            ORDER BY severity DESC, name
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_agents() -> list[dict[str, Any]]:
    """Return all registered agents."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT id, name, owner, status, framework,
                   model_version, created_at
            FROM agents
            ORDER BY created_at DESC
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_decision_counts() -> dict[str, int]:
    """Return count of allow/deny/review decisions across all events."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT decision, COUNT(*) as count
            FROM audit_events
            GROUP BY decision
        """)).mappings().all()
    counts = {"allow": 0, "deny": 0, "review": 0}
    for row in rows:
        decision = row["decision"].lower()
        if decision in counts:
            counts[decision] = int(row["count"])
    return counts


def get_risk_scores() -> list[dict[str, Any]]:
    """Return risk score progression per session for chart."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT
                s.id AS session_id,
                ae.sequence_number,
                SUM(ae.risk_delta) OVER (
                    PARTITION BY ae.session_id
                    ORDER BY ae.sequence_number
                ) AS cumulative_risk,
                ae.created_at
            FROM audit_events ae
            JOIN sessions s ON ae.session_id = s.id
            ORDER BY ae.session_id, ae.sequence_number
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_tokens() -> list[dict[str, Any]]:
    """Return all API token metadata. Never returns the token string itself."""
    with get_sync_session() as session:
        rows = session.execute(text("""
            SELECT id, role, description, revoked, created_at
            FROM api_tokens
            ORDER BY created_at DESC
        """)).mappings().all()
    return [dict(r) for r in rows]
