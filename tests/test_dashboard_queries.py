"""Tests for dashboard query functions against live DB."""
import pytest


def test_get_audit_events_returns_list():
    """get_audit_events must return a list."""
    from dashboard.queries import get_audit_events
    result = get_audit_events(limit=10)
    assert isinstance(result, list)


def test_get_audit_events_fields():
    """Each audit event must have required display fields."""
    from dashboard.queries import get_audit_events
    results = get_audit_events(limit=10)
    if results:
        row = results[0]
        for field in ["tool_name", "decision", "created_at"]:
            assert field in row, f"Missing field: {field}"


def test_get_policies_returns_list():
    """get_policies must return a list."""
    from dashboard.queries import get_policies
    result = get_policies()
    assert isinstance(result, list)


def test_get_agents_returns_list():
    """get_agents must return a list."""
    from dashboard.queries import get_agents
    result = get_agents()
    assert isinstance(result, list)


def test_get_decision_counts_returns_dict():
    """get_decision_counts must return dict with allow/deny/review keys."""
    from dashboard.queries import get_decision_counts
    result = get_decision_counts()
    assert isinstance(result, dict)
    for key in ["allow", "deny", "review"]:
        assert key in result


def test_get_risk_scores_returns_list():
    """get_risk_scores must return a list of session risk data."""
    from dashboard.queries import get_risk_scores
    result = get_risk_scores()
    assert isinstance(result, list)
