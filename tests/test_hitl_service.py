"""Tests for HITL service — review row creation and Slack message."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_hitl_review_adds_row():
    """create_hitl_review must add a HITLReview row to the session."""
    from app.services.hitl_service import create_hitl_review

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    review_id = await create_hitl_review(
        session=mock_session,
        audit_event_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        assigned_to="compliance-team",
    )

    assert mock_session.add.called
    assert review_id is not None


@pytest.mark.asyncio
async def test_post_slack_review_calls_slack_api():
    """post_slack_review must call Slack chat.postMessage."""
    from app.services.hitl_service import post_slack_review

    mock_client = MagicMock()
    mock_client.chat_postMessage = MagicMock(
        return_value={"ok": True, "ts": "12345.678"}
    )

    with patch("app.services.hitl_service.WebClient", return_value=mock_client):
        await post_slack_review(
            review_id=uuid.uuid4(),
            audit_event_id=uuid.uuid4(),
            agent_name="test-agent",
            tool_name="http_request",
            tool_parameters={"url": "https://example.com"},
            decision_reason="requires_human_review",
        )

    assert mock_client.chat_postMessage.called


@pytest.mark.asyncio
async def test_post_slack_review_includes_tool_name():
    """Slack message must include the tool name."""
    from app.services.hitl_service import post_slack_review

    mock_client = MagicMock()
    posted_blocks = []

    def capture_post(**kwargs):
        posted_blocks.append(kwargs)
        return {"ok": True, "ts": "12345.678"}

    mock_client.chat_postMessage = capture_post

    with patch("app.services.hitl_service.WebClient", return_value=mock_client):
        await post_slack_review(
            review_id=uuid.uuid4(),
            audit_event_id=uuid.uuid4(),
            agent_name="test-agent",
            tool_name="http_request",
            tool_parameters={},
            decision_reason="requires_human_review",
        )

    assert len(posted_blocks) == 1
    assert "http_request" in str(posted_blocks[0])
