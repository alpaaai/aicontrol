"""Tests for OPA client — decision evaluation."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_evaluate_returns_allow_for_safe_tool():
    """evaluate() must return allow for a tool not on any blacklist."""
    from app.services.opa_client import evaluate

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {"decision": "allow", "reason": "default_allow"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await evaluate("safe_tool", {}, [])

    assert result["decision"] == "allow"


@pytest.mark.asyncio
async def test_evaluate_returns_deny_for_blacklisted_tool():
    """evaluate() must return deny when OPA says deny."""
    from app.services.opa_client import evaluate

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {"decision": "deny", "reason": "tool_denylisted"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await evaluate("execute_code", {}, [])

    assert result["decision"] == "deny"


@pytest.mark.asyncio
async def test_evaluate_includes_reason():
    """evaluate() result must always include a reason field."""
    from app.services.opa_client import evaluate

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {"decision": "allow", "reason": "default_allow"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await evaluate("any_tool", {}, [])

    assert "reason" in result
