"""HITL service — creates review rows and posts Slack notifications."""
import json
import uuid
from typing import Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import HITLReview

logger = get_logger("hitl_service")


async def create_hitl_review(
    session: AsyncSession,
    audit_event_id: uuid.UUID,
    session_id: uuid.UUID,
    assigned_to: str = "compliance-team",
) -> uuid.UUID:
    """Create a pending HITLReview row. Returns its UUID."""
    review = HITLReview(
        id=uuid.uuid4(),
        audit_event_id=audit_event_id,
        session_id=session_id,
        status="pending",
        assigned_to=assigned_to,
        notified_via="slack",
    )
    session.add(review)
    await session.flush()
    logger.info(
        "hitl_review_created",
        review_id=str(review.id),
        audit_event_id=str(audit_event_id),
    )
    return review.id


async def post_slack_review(
    review_id: uuid.UUID,
    audit_event_id: uuid.UUID,
    agent_name: str,
    tool_name: str,
    tool_parameters: dict[str, Any],
    decision_reason: str,
) -> Optional[str]:
    """Post interactive Slack message with approve/deny buttons.
    Returns Slack message ts or None on failure.
    """
    if not settings.slack_bot_token or \
       settings.slack_bot_token == "xoxb-placeholder":
        logger.warning("slack_skipped", reason="SLACK_BOT_TOKEN not configured")
        return None

    client = WebClient(token=settings.slack_bot_token)
    params_preview = json.dumps(tool_parameters, indent=2)[:300]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Agent Tool Call Requires Review",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Agent:*\n{agent_name}"},
                {"type": "mrkdwn", "text": f"*Tool:*\n`{tool_name}`"},
                {"type": "mrkdwn", "text": f"*Reason:*\n{decision_reason}"},
                {"type": "mrkdwn",
                 "text": f"*Review ID:*\n`{str(review_id)[:8]}...`"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Parameters:*\n```{params_preview}```",
            },
        },
        {
            "type": "actions",
            "block_id": f"hitl_{review_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "action_id": "hitl_approve",
                    "value": str(review_id),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Deny"},
                    "style": "danger",
                    "action_id": "hitl_deny",
                    "value": str(review_id),
                },
            ],
        },
    ]

    try:
        response = client.chat_postMessage(
            channel=settings.slack_review_channel,
            text=f"Agent `{agent_name}` wants to call `{tool_name}` — review required",
            blocks=blocks,
        )
        ts = response.get("ts")
        logger.info(
            "slack_message_sent",
            review_id=str(review_id),
            channel=settings.slack_review_channel,
            ts=ts,
        )
        return ts
    except SlackApiError as e:
        logger.error("slack_message_failed", error=str(e),
                     review_id=str(review_id))
        return None
