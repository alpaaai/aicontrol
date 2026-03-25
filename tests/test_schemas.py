"""Tests that all ORM models are defined with correct columns and types."""
from sqlalchemy import inspect as sa_inspect


def _cols(model) -> dict:
    mapper = sa_inspect(model)
    return {prop.key: prop for prop in mapper.mapper.column_attrs}


def test_agents_table_name():
    from app.models.schemas import Agent
    assert Agent.__tablename__ == "agents"


def test_agents_required_columns():
    from app.models.schemas import Agent
    cols = _cols(Agent)
    for name in ["id", "name", "owner", "status", "approved_tools", "created_at"]:
        assert name in cols, f"agents missing column: {name}"


def test_agents_approved_tools_is_json():
    from app.models.schemas import Agent
    from sqlalchemy import JSON
    cols = _cols(Agent)
    assert isinstance(cols["approved_tools"].columns[0].type, JSON)


def test_sessions_table_name():
    from app.models.schemas import Session
    assert Session.__tablename__ == "sessions"


def test_sessions_fk_to_agents():
    from app.models.schemas import Session
    cols = _cols(Session)
    assert "agent_id" in cols
    fks = list(cols["agent_id"].columns[0].foreign_keys)
    assert len(fks) == 1
    assert "agents.id" in str(fks[0])


def test_policies_table_name():
    from app.models.schemas import Policy
    assert Policy.__tablename__ == "policies"


def test_policies_required_columns():
    from app.models.schemas import Policy
    cols = _cols(Policy)
    for name in ["id", "name", "rule_type", "condition", "action", "active"]:
        assert name in cols, f"policies missing column: {name}"


def test_audit_events_table_name():
    from app.models.schemas import AuditEvent
    assert AuditEvent.__tablename__ == "audit_events"


def test_audit_events_required_columns():
    from app.models.schemas import AuditEvent
    cols = _cols(AuditEvent)
    for name in ["id", "session_id", "sequence_number", "agent_id",
                 "tool_name", "decision", "created_at"]:
        assert name in cols, f"audit_events missing column: {name}"


def test_hitl_reviews_table_name():
    from app.models.schemas import HITLReview
    assert HITLReview.__tablename__ == "hitl_reviews"


def test_hitl_reviews_fk_to_audit_events():
    from app.models.schemas import HITLReview
    cols = _cols(HITLReview)
    assert "audit_event_id" in cols
    fks = list(cols["audit_event_id"].columns[0].foreign_keys)
    assert len(fks) == 1
    assert "audit_events.id" in str(fks[0])


def test_all_five_models_exist():
    from app.models import schemas
    for name in ["Agent", "Session", "Policy", "AuditEvent", "HITLReview"]:
        assert hasattr(schemas, name), f"Missing model: {name}"
