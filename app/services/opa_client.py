"""Async OPA client — evaluates tool calls against loaded policies."""
from typing import Any

import httpx

from app.core.config import settings

OPA_ENDPOINT = f"{settings.opa_url}/v1/data/aicontrol"


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
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(OPA_ENDPOINT, json=payload)
        response.raise_for_status()

    result = response.json().get("result", {})
    return {
        "decision": result.get("decision", "allow"),
        "reason": result.get("reason", "default_allow"),
    }
