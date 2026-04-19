"""Async OPA client — evaluates tool calls against loaded policies."""
import datetime
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

OPA_ENDPOINT = f"{settings.opa_url}/v1/data/aicontrol"
logger = get_logger("opa_client")


def _current_time_context() -> dict[str, int]:
    """Return current UTC day-of-week (0=Mon…6=Sun) and hour for temporal policy evaluation."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "day_of_week": now.weekday(),
        "hour": now.hour,
    }


async def evaluate(
    tool_name: str,
    tool_parameters: dict[str, Any],
    policies: list[dict],
) -> dict[str, str]:
    """
    Send tool call context to OPA and return the decision.

    Returns dict with keys: decision (allow|deny|review), reason (str)
    """
    payload = {
        "input": {
            "tool_name": tool_name,
            "tool_parameters": tool_parameters,
            "policies": policies,
            "current_time": _current_time_context(),
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(OPA_ENDPOINT, json=payload)
        response.raise_for_status()

    result = response.json().get("result", {})
    decision = result.get("decision", "allow")
    logger.info("opa_evaluated", tool_name=tool_name, decision=decision)
    return {
        "decision": decision,
        "reason": result.get("reason", "default_allow"),
    }
