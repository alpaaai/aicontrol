"""Tests for Slack actions endpoint."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_slack_actions_route_exists():
    """POST /slack/actions route must be registered."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/slack/actions" in routes


@pytest.mark.asyncio
async def test_slack_actions_rejects_bad_signature():
    """POST /slack/actions with invalid signature must return 403."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/slack/actions",
            content="payload={}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_handle_approve_updates_review():
    """handle_action must update hitl_review status to approved."""
    from app.routers.slack_actions import handle_action

    mock_session = AsyncMock()
    mock_review = MagicMock()
    mock_review.status = "pending"
    mock_session.get = AsyncMock(return_value=mock_review)
    mock_session.flush = AsyncMock()

    with patch("app.routers.slack_actions.WebClient"):
        await handle_action(
            session=mock_session,
            action_id="hitl_approve",
            review_id=uuid.uuid4(),
            reviewer="U123456",
        )

    assert mock_review.status == "approved"
    assert mock_review.reviewer == "U123456"
