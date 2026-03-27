"""Loads policies from YAML, upserts to Postgres, pushes Rego to OPA."""
from pathlib import Path
from typing import Any

import httpx
import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

POLICIES_YAML = Path(__file__).parent.parent.parent / "policies" / "policies.yaml"
REGO_BUNDLE = Path(__file__).parent.parent.parent / "policies" / "base.rego"


def load_yaml() -> list[dict[str, Any]]:
    """Read and parse policies/policies.yaml."""
    with open(POLICIES_YAML) as f:
        data = yaml.safe_load(f)
    return data["policies"]


async def upsert_policies(session: AsyncSession, policies: list[dict]) -> None:
    """Insert or update each policy row in Postgres."""
    for p in policies:
        await session.execute(
            text("""
                INSERT INTO policies
                    (id, name, description, rule_type, condition, action,
                     compliance_frameworks, severity, active)
                VALUES
                    (gen_random_uuid(), :name, :description, :rule_type,
                     CAST(:condition AS jsonb), :action,
                     CAST(:compliance_frameworks AS jsonb), :severity, true)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    rule_type = EXCLUDED.rule_type,
                    condition = EXCLUDED.condition,
                    action = EXCLUDED.action,
                    compliance_frameworks = EXCLUDED.compliance_frameworks,
                    severity = EXCLUDED.severity,
                    active = true
            """),
            {
                "name": p["name"],
                "description": p.get("description", ""),
                "rule_type": p["rule_type"],
                "condition": __import__("json").dumps(p["condition"]),
                "action": p["action"],
                "compliance_frameworks": __import__("json").dumps(
                    p.get("compliance_frameworks", [])
                ),
                "severity": p.get("severity", "medium"),
            },
        )
    await session.commit()


async def push_rego_to_opa() -> None:
    """Push base.rego to OPA as a policy bundle."""
    rego_content = REGO_BUNDLE.read_text()
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.opa_url}/v1/policies/aicontrol",
            content=rego_content,
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()


async def load_all(session: AsyncSession) -> None:
    """Full startup sequence: YAML → Postgres → OPA."""
    policies = load_yaml()
    await upsert_policies(session, policies)
    await push_rego_to_opa()
