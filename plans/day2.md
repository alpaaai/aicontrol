# AIControl Day 2 — MCP Proxy + Policy Intercept Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working HTTP intercept proxy — agent POSTs a tool call, OPA evaluates it against policies loaded from Postgres, decision is returned (allow/deny/review), and the event is written to `audit_events`.

**Architecture:** Policies are defined in `policies/policies.yaml` (source of truth), loaded into Postgres and pushed to OPA as a Rego bundle at startup. Every tool call hits `POST /intercept`, which queries OPA, writes to `audit_events`, and returns the decision. Full intercept loop demonstrable via curl.

**Tech Stack:** FastAPI, SQLAlchemy async, OPA REST API, PyYAML, httpx (async OPA client), Pydantic v2

---

## File Map

| File | Purpose |
|---|---|
| `policies/policies.yaml` | Source-of-truth policy definitions (YAML) |
| `policies/base.rego` | Rego policy bundle pushed to OPA at startup |
| `app/services/__init__.py` | Package marker |
| `app/services/policy_loader.py` | Reads YAML, upserts policies into Postgres, pushes Rego to OPA |
| `app/services/opa_client.py` | Async httpx client — sends tool call to OPA, returns decision |
| `app/services/audit_writer.py` | Writes one `AuditEvent` row per intercept |
| `app/routers/__init__.py` | Package marker |
| `app/routers/intercept.py` | `POST /intercept` endpoint — orchestrates evaluate → audit → respond |
| `app/routers/policies.py` | `GET /policies` — list active policies (for dashboard/debugging) |
| `app/main.py` | Updated — mounts routers, runs policy loader on startup |
| `scripts/seed.py` | Inserts a test agent and session so demo curl works |
| `migrations/versions/<hash>_add_policy_indexes.py` | Migration adding indexes on audit_events(session_id, agent_id) |

---

## Task 1: Policy YAML + Rego Bundle

`policies/policies.yaml` — human-readable policy definitions. `policies/base.rego` — the Rego rules OPA evaluates. These two files are the governance configuration an operator edits.

**Files:**
- Create: `policies/policies.yaml`
- Create: `policies/base.rego`

- [x] **Step 1: Create `policies/` directory**

```bash
mkdir -p ~/aicontrol/policies
```

- [x] **Step 2: Create `policies/policies.yaml`**

```bash
cat > ~/aicontrol/policies/policies.yaml << 'EOF'
policies:
  - name: block_dangerous_tools
    description: Block tools that can execute arbitrary code or delete data
    rule_type: tool_blacklist
    condition:
      blocked_tools:
        - execute_code
        - delete_database
        - drop_table
        - shell_exec
        - rm_rf
    action: deny
    severity: critical
    compliance_frameworks: ["SOC2", "ISO27001"]

  - name: require_review_for_external_calls
    description: Flag any tool that makes external HTTP requests for human review
    rule_type: tool_pattern
    condition:
      tool_name_contains: ["http_request", "webhook", "external_api"]
    action: review
    severity: high
    compliance_frameworks: ["SOC2"]

  - name: allow_standard_tools
    description: Allow all other tools by default
    rule_type: default_allow
    condition: {}
    action: allow
    severity: low
    compliance_frameworks: []
EOF
```

- [x] **Step 3: Create `policies/base.rego`**

```bash
cat > ~/aicontrol/policies/base.rego << 'EOF'
package aicontrol

import future.keywords.if
import future.keywords.in

default decision := "allow"
default reason := "default_allow"

# Deny if tool is on the blacklist
decision := "deny" if {
    some policy in input.policies
    policy.rule_type == "tool_blacklist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
}

reason := "tool_blacklisted" if {
    some policy in input.policies
    policy.rule_type == "tool_blacklist"
    policy.action == "deny"
    input.tool_name in policy.condition.blocked_tools
}

# Review if tool name matches a pattern
decision := "review" if {
    decision != "deny"
    some policy in input.policies
    policy.rule_type == "tool_pattern"
    policy.action == "review"
    some pattern in policy.condition.tool_name_contains
    contains(input.tool_name, pattern)
}

reason := "requires_human_review" if {
    decision != "deny"
    some policy in input.policies
    policy.rule_type == "tool_pattern"
    policy.action == "review"
    some pattern in policy.condition.tool_name_contains
    contains(input.tool_name, pattern)
}
EOF
```

- [x] **Step 4: Commit**

```bash
cd ~/aicontrol
git add policies/
git commit -m "feat: add policy yaml and rego bundle"
```

---

## Task 2: Policy Loader Service

`app/services/policy_loader.py` — reads `policies.yaml`, upserts each policy into the `policies` table, then pushes `base.rego` to OPA's REST API. Called once at app startup.

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/policy_loader.py`
- Create: `tests/test_policy_loader.py`

- [x] **Step 1: Create package marker**

```bash
touch ~/aicontrol/app/services/__init__.py
```

- [x] **Step 2: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_policy_loader.py << 'EOF'
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
EOF
```

- [x] **Step 3: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_policy_loader.py -v
```
Expected: `ImportError` for `app.services.policy_loader`.

- [x] **Step 4: Write `app/services/policy_loader.py`**

```bash
cat > ~/aicontrol/app/services/policy_loader.py << 'EOF'
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
                    (name, description, rule_type, condition, action,
                     compliance_frameworks, severity, active)
                VALUES
                    (:name, :description, :rule_type, :condition::jsonb, :action,
                     :compliance_frameworks::jsonb, :severity, true)
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
EOF
```

- [x] **Step 5: Add unique constraint on policies.name — new migration**

```bash
cd ~/aicontrol
alembic revision --autogenerate -m "add_policies_name_unique"
```

Check the generated file adds `unique=True` on `policies.name`. If autogenerate missed it, edit manually:

```bash
# Open the generated file and verify it contains:
# op.create_unique_constraint('uq_policies_name', 'policies', ['name'])
# If missing, add it manually to the upgrade() function.
```

Apply:
```bash
alembic upgrade head
```

- [x] **Step 6: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_policy_loader.py -v
```
Expected: `3 passed`.

- [x] **Step 7: Commit**

```bash
cd ~/aicontrol
git add app/services/ tests/test_policy_loader.py migrations/
git commit -m "feat: add policy loader service with yaml upsert and opa push"
```

---

## Task 3: OPA Client Service

`app/services/opa_client.py` — async httpx client that sends a tool call to OPA's `/v1/data/aicontrol` endpoint and returns the decision. Takes tool name, parameters, and the current active policies as input.

**Files:**
- Create: `app/services/opa_client.py`
- Create: `tests/test_opa_client.py`

- [x] **Step 1: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_opa_client.py << 'EOF'
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
        "result": {"decision": "deny", "reason": "tool_blacklisted"}
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
EOF
```

- [x] **Step 2: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_opa_client.py -v
```
Expected: `ImportError` for `app.services.opa_client`.

- [x] **Step 3: Write `app/services/opa_client.py`**

```bash
cat > ~/aicontrol/app/services/opa_client.py << 'EOF'
"""Async OPA client — evaluates tool calls against loaded policies."""
import json
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
EOF
```

- [x] **Step 4: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_opa_client.py -v
```
Expected: `3 passed`.

- [x] **Step 5: Commit**

```bash
cd ~/aicontrol
git add app/services/opa_client.py tests/test_opa_client.py
git commit -m "feat: add async opa client service"
```

---

## Task 4: Audit Writer Service

`app/services/audit_writer.py` — writes one row to `audit_events` for every intercept, regardless of decision. This is the immutable audit trail.

**Files:**
- Create: `app/services/audit_writer.py`
- Create: `tests/test_audit_writer.py`

- [x] **Step 1: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_audit_writer.py << 'EOF'
"""Tests for audit writer — event persistence."""
import uuid
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_write_event_calls_session_add():
    """write_event must add an AuditEvent to the session."""
    from app.services.audit_writer import write_event

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.flush = AsyncMock()

    event_id = await write_event(
        session=mock_session,
        session_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        agent_name="test-agent",
        tool_name="safe_tool",
        tool_parameters={"key": "value"},
        decision="allow",
        decision_reason="default_allow",
        sequence_number=1,
        duration_ms=42,
    )

    assert mock_session.add.called
    assert event_id is not None


@pytest.mark.asyncio
async def test_write_event_returns_uuid():
    """write_event must return a UUID for the created event."""
    from app.services.audit_writer import write_event

    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.flush = AsyncMock()

    event_id = await write_event(
        session=mock_session,
        session_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        agent_name="test-agent",
        tool_name="safe_tool",
        tool_parameters={},
        decision="deny",
        decision_reason="tool_blacklisted",
        sequence_number=2,
        duration_ms=10,
    )

    assert isinstance(event_id, uuid.UUID)
EOF
```

- [x] **Step 2: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_audit_writer.py -v
```
Expected: `ImportError` for `app.services.audit_writer`.

- [x] **Step 3: Write `app/services/audit_writer.py`**

```bash
cat > ~/aicontrol/app/services/audit_writer.py << 'EOF'
"""Writes immutable audit events for every intercepted tool call."""
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AuditEvent


async def write_event(
    session: AsyncSession,
    session_id: uuid.UUID,
    agent_id: uuid.UUID,
    agent_name: str,
    tool_name: str,
    tool_parameters: dict[str, Any],
    decision: str,
    decision_reason: str,
    sequence_number: int,
    duration_ms: int,
    policy_id: Optional[uuid.UUID] = None,
    policy_name: Optional[str] = None,
    tool_response: Optional[dict] = None,
    risk_delta: int = 0,
) -> uuid.UUID:
    """Persist one audit event. Returns the new event's UUID."""
    event = AuditEvent(
        session_id=session_id,
        agent_id=agent_id,
        agent_name=agent_name,
        tool_name=tool_name,
        tool_parameters=tool_parameters,
        tool_response=tool_response,
        policy_id=policy_id,
        policy_name=policy_name,
        decision=decision,
        decision_reason=decision_reason,
        sequence_number=sequence_number,
        duration_ms=duration_ms,
        risk_delta=risk_delta,
    )
    session.add(event)
    await session.flush()
    return event.id
EOF
```

- [x] **Step 4: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_audit_writer.py -v
```
Expected: `2 passed`.

- [x] **Step 5: Commit**

```bash
cd ~/aicontrol
git add app/services/audit_writer.py tests/test_audit_writer.py
git commit -m "feat: add audit writer service"
```

---

## Task 5: Intercept Router

`app/routers/intercept.py` — the core endpoint. `POST /intercept` receives a tool call, loads active policies from Postgres, evaluates via OPA, writes to audit_events, returns decision.

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/intercept.py`
- Create: `tests/test_intercept.py`

- [x] **Step 1: Create package marker**

```bash
touch ~/aicontrol/app/routers/__init__.py
```

- [x] **Step 2: Write the failing tests**

```bash
cat > ~/aicontrol/tests/test_intercept.py << 'EOF'
"""Tests for POST /intercept endpoint."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


def make_payload(tool_name="safe_tool"):
    return {
        "session_id": str(uuid.uuid4()),
        "agent_id": str(uuid.uuid4()),
        "agent_name": "test-agent",
        "tool_name": tool_name,
        "tool_parameters": {"key": "value"},
        "sequence_number": 1,
    }


@pytest.mark.asyncio
async def test_intercept_returns_200():
    """POST /intercept must return HTTP 200."""
    from app.main import app

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "allow", "reason": "default_allow"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=uuid.uuid4()
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_intercept_returns_decision():
    """POST /intercept response must include decision field."""
    from app.main import app

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "deny", "reason": "tool_blacklisted"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=uuid.uuid4()
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload("execute_code"))

    data = response.json()
    assert "decision" in data
    assert data["decision"] == "deny"


@pytest.mark.asyncio
async def test_intercept_returns_audit_event_id():
    """POST /intercept response must include audit_event_id."""
    from app.main import app
    event_id = uuid.uuid4()

    with patch("app.routers.intercept.evaluate", new=AsyncMock(
        return_value={"decision": "allow", "reason": "default_allow"}
    )), patch("app.routers.intercept.write_event", new=AsyncMock(
        return_value=event_id
    )), patch("app.routers.intercept.get_active_policies", new=AsyncMock(
        return_value=[]
    )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/intercept", json=make_payload())

    data = response.json()
    assert "audit_event_id" in data
    assert data["audit_event_id"] == str(event_id)
EOF
```

- [x] **Step 3: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_intercept.py -v
```
Expected: `ImportError` for `app.routers.intercept`.

- [x] **Step 4: Write `app/routers/intercept.py`**

```bash
cat > ~/aicontrol/app/routers/intercept.py << 'EOF'
"""POST /intercept — core tool call intercept endpoint."""
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import Policy
from app.services.opa_client import evaluate
from app.services.audit_writer import write_event

router = APIRouter()


class InterceptRequest(BaseModel):
    session_id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str
    tool_name: str
    tool_parameters: dict[str, Any] = {}
    sequence_number: int


class InterceptResponse(BaseModel):
    decision: str
    reason: str
    audit_event_id: uuid.UUID


async def get_active_policies(session: AsyncSession) -> list[dict]:
    """Load all active policies from Postgres as plain dicts for OPA."""
    result = await session.execute(
        select(Policy).where(Policy.active == True)
    )
    policies = result.scalars().all()
    return [
        {
            "name": p.name,
            "rule_type": p.rule_type,
            "condition": p.condition,
            "action": p.action,
            "severity": p.severity,
        }
        for p in policies
    ]


@router.post("/intercept", response_model=InterceptResponse)
async def intercept(
    request: InterceptRequest,
    db: AsyncSession = Depends(get_db),
) -> InterceptResponse:
    """
    Intercept a tool call, evaluate against policies, write audit event.
    Returns allow | deny | review plus the audit event ID.
    """
    start = time.monotonic()

    # Load active policies from DB
    policies = await get_active_policies(db)

    # Evaluate via OPA
    opa_result = await evaluate(
        tool_name=request.tool_name,
        tool_parameters=request.tool_parameters,
        policies=policies,
    )

    duration_ms = int((time.monotonic() - start) * 1000)

    # Write immutable audit event
    event_id = await write_event(
        session=db,
        session_id=request.session_id,
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        tool_name=request.tool_name,
        tool_parameters=request.tool_parameters,
        decision=opa_result["decision"],
        decision_reason=opa_result["reason"],
        sequence_number=request.sequence_number,
        duration_ms=duration_ms,
    )

    return InterceptResponse(
        decision=opa_result["decision"],
        reason=opa_result["reason"],
        audit_event_id=event_id,
    )
EOF
```

- [x] **Step 5: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_intercept.py -v
```
Expected: `3 passed`.

- [x] **Step 6: Commit**

```bash
cd ~/aicontrol
git add app/routers/ tests/test_intercept.py
git commit -m "feat: add intercept router with policy eval and audit logging"
```

---

## Task 6: Wire Everything into app/main.py

`app/main.py` — updated to mount the intercept router and run the policy loader on startup (loads YAML → Postgres → OPA when the server boots).

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_startup.py`

- [x] **Step 1: Write the failing test**

```bash
cat > ~/aicontrol/tests/test_startup.py << 'EOF'
"""Tests that routers are mounted and startup runs."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_intercept_route_exists():
    """POST /intercept route must be registered on the app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/intercept" in routes


@pytest.mark.asyncio
async def test_health_still_works():
    """GET /health must still return 200 after router changes."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
EOF
```

- [x] **Step 2: Run tests — verify they FAIL**

```bash
cd ~/aicontrol && pytest tests/test_startup.py -v
```
Expected: `FAILED test_intercept_route_exists` — router not mounted yet.

- [x] **Step 3: Update `app/main.py`**

```bash
cat > ~/aicontrol/app/main.py << 'EOF'
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.database import async_session_factory
from app.routers.intercept import router as intercept_router
from app.services.policy_loader import load_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run policy loader on startup."""
    async with async_session_factory() as session:
        await load_all(session)
    yield


app = FastAPI(
    title="AIControl",
    description="Enterprise AI agent governance middleware",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(intercept_router)


@app.get("/health")
async def health() -> dict:
    """Liveness check."""
    return {"status": "ok", "service": "aicontrol"}
EOF
```

- [x] **Step 4: Run tests — verify they PASS**

```bash
cd ~/aicontrol && pytest tests/test_startup.py -v
```
Expected: `2 passed`.

- [x] **Step 5: Run full test suite**

```bash
cd ~/aicontrol && pytest tests/ -v
```
Expected: All tests pass across all test files.

- [x] **Step 6: Commit**

```bash
cd ~/aicontrol
git add app/main.py tests/test_startup.py
git commit -m "feat: mount intercept router and run policy loader on startup"
```

---

## Task 7: Seed Script + End-to-End Demo

`scripts/seed.py` — inserts a test agent and session into Postgres so curl demo calls have valid UUIDs to reference.

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/seed.py`

- [x] **Step 1: Create seed script**

```bash
mkdir -p ~/aicontrol/scripts
cat > ~/aicontrol/scripts/seed.py << 'EOF'
"""Insert demo agent and session for manual testing."""
import asyncio
import uuid
from sqlalchemy import text
from app.models.database import async_session_factory

AGENT_ID = "00000000-0000-0000-0000-000000000001"
SESSION_ID = "00000000-0000-0000-0000-000000000002"


async def seed():
    async with async_session_factory() as session:
        await session.execute(text("""
            INSERT INTO agents (id, name, owner, status, approved_tools)
            VALUES (:id, :name, :owner, :status, :tools::jsonb)
            ON CONFLICT (id) DO NOTHING
        """), {"id": AGENT_ID, "name": "demo-agent",
               "owner": "demo@aicontrol.dev", "status": "approved",
               "tools": '["safe_tool", "http_request"]'})

        await session.execute(text("""
            INSERT INTO sessions (id, agent_id, status)
            VALUES (:id, :agent_id, :status)
            ON CONFLICT (id) DO NOTHING
        """), {"id": SESSION_ID, "agent_id": AGENT_ID, "status": "active"})

        await session.commit()
        print(f"Seeded agent_id={AGENT_ID}")
        print(f"Seeded session_id={SESSION_ID}")


asyncio.run(seed())
EOF
```

- [x] **Step 2: Start the server**

```bash
cd ~/aicontrol
uvicorn app.main:app --reload --port 8000
```

Expected: Server starts, policy loader runs, no errors. You should see log lines about policies being loaded.

- [x] **Step 3: Run seed script (in a second terminal)**

```bash
cd ~/aicontrol && python scripts/seed.py
```

Expected:
```
Seeded agent_id=00000000-0000-0000-0000-000000000001
Seeded session_id=00000000-0000-0000-0000-000000000002
```

- [x] **Step 4: Demo curl — allowed tool**

```bash
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "00000000-0000-0000-0000-000000000002",
    "agent_id": "00000000-0000-0000-0000-000000000001",
    "agent_name": "demo-agent",
    "tool_name": "safe_tool",
    "tool_parameters": {"query": "hello"},
    "sequence_number": 1
  }' | python3 -m json.tool
```

Expected: `"decision": "allow"`

- [x] **Step 5: Demo curl — blocked tool**

```bash
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "00000000-0000-0000-0000-000000000002",
    "agent_id": "00000000-0000-0000-0000-000000000001",
    "agent_name": "demo-agent",
    "tool_name": "execute_code",
    "tool_parameters": {"code": "rm -rf /"},
    "sequence_number": 2
  }' | python3 -m json.tool
```

Expected: `"decision": "deny"`

- [x] **Step 6: Demo curl — review tool**

```bash
curl -s -X POST http://localhost:8000/intercept \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "00000000-0000-0000-0000-000000000002",
    "agent_id": "00000000-0000-0000-0000-000000000001",
    "agent_name": "demo-agent",
    "tool_name": "http_request",
    "tool_parameters": {"url": "https://example.com"},
    "sequence_number": 3
  }' | python3 -m json.tool
```

Expected: `"decision": "review"`

- [x] **Step 7: Verify audit events were written**

```bash
docker compose exec postgres psql -U aicontrol -d aicontrol \
  -c "SELECT tool_name, decision, decision_reason FROM audit_events ORDER BY created_at;"
```

Expected: 3 rows — safe_tool/allow, execute_code/deny, http_request/review.

- [x] **Step 8: Final commit**

```bash
cd ~/aicontrol
git add scripts/
git commit -m "feat: add seed script and verify end-to-end intercept loop"
```

---

## Troubleshooting Quick Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `push_rego_to_opa` fails on startup | OPA not running | `docker compose up -d` |
| OPA returns empty result | Rego syntax error | `docker compose logs opa` |
| `ON CONFLICT (name)` error on migration | Unique constraint not added | Check migration file, run `alembic upgrade head` |
| `/intercept` returns 422 | Request body missing required field | Check all fields in curl payload |
| `audit_events` stays empty | `write_event` not flushing | Check `session.flush()` is called |
| OPA decision always `allow` | Policies not loaded into OPA | Check startup logs for `push_rego_to_opa` errors |
