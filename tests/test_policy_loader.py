"""Tests for policy loader — YAML parsing and DB upsert logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


def test_load_yaml_returns_list_of_policies():
    """load_yaml must return a list of dicts with required keys."""
    from app.services.policy_loader import load_yaml
    policies = load_yaml()
    assert isinstance(policies, list)
    assert len(policies) > 0
    for p in policies:
        assert "name" in p
        assert "rule_type" in p
        assert "action" in p
        assert "condition" in p


def test_load_yaml_actions_are_valid():
    """All policy actions must be allow, deny, or review."""
    from app.services.policy_loader import load_yaml
    valid_actions = {"allow", "deny", "review"}
    for p in load_yaml():
        assert p["action"] in valid_actions, f"Invalid action: {p['action']}"


@pytest.mark.asyncio
async def test_upsert_policies_calls_db():
    """upsert_policies must execute one upsert per policy."""
    from app.services.policy_loader import upsert_policies

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    policies = [
        {"name": "test", "description": "", "rule_type": "default_allow",
         "condition": {}, "action": "allow", "severity": "low",
         "compliance_frameworks": []}
    ]
    await upsert_policies(mock_session, policies)
    assert mock_session.execute.called
