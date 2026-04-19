# Integration

AIControl integrates at the tool execution layer. Before your agent runs a tool, it sends a single HTTP call to `/intercept`. AIControl returns a decision. Your agent acts on it.

This page covers the intercept contract in full. For copy-paste wrappers for specific frameworks, see [Integrations](/docs/integrations).

---

## The integration pattern

```
Agent decides to call a tool
        ↓
POST /intercept  →  decision returned in < 10ms
        ↓
allow   → execute the tool
deny    → abort, surface the reason to the agent
review  → a human has been notified; see below for handling
```

Every intercept — regardless of decision — is written to the audit log before the response is returned.

---

## Environment setup

Set these environment variables in your agent's deployment config. Never hardcode tokens.

```bash
AICONTROL_URL=http://your-aicontrol-host:8000   # required
AICONTROL_TOKEN=eyJhbGc...                       # required — agent-role JWT
AGENT_NAME=loan-underwriting-agent               # optional — appears in audit trail
AGENT_ID=uuid                                    # optional — stable agent identity
```

`AGENT_ID` is auto-generated as a random UUID if not set. For consistent audit trail attribution across restarts, set it to a stable value (or use the agent ID from `POST /agents`).

---

## The intercept request

```
POST /intercept
Authorization: Bearer <agent-token>
Content-Type: application/json
```

```json
{
  "session_id": "b3e1f9a2-...",
  "agent_id": "7c4d2e8f-...",
  "agent_name": "loan-underwriting-agent",
  "tool_name": "query_credit_bureau",
  "tool_parameters": {
    "applicant_id": "A-10042",
    "report_type": "full"
  },
  "sequence_number": 3
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `session_id` | UUID | yes | Groups all tool calls within one agent run |
| `agent_id` | UUID | yes | Stable agent identity — matches your registered agent |
| `agent_name` | string | yes | Readable name; appears in dashboard and Slack notifications |
| `tool_name` | string | yes | The tool being called — matched against policies |
| `tool_parameters` | object | yes | Full parameters at time of call; stored in audit record |
| `sequence_number` | integer | yes | Call order within the session; starts at 1 |

Generate `session_id` once per agent run (not per tool call). Use the same `session_id` across all tool calls in that session so they group correctly in the audit log.

---

## The intercept response

```json
{
  "decision": "allow",
  "reason": "default_allow",
  "audit_event_id": "3f2a1c8b-...",
  "review_id": null,
  "duration_ms": 7
}
```

| Field | Values | Notes |
|-------|--------|-------|
| `decision` | `allow` \| `deny` \| `review` | What your agent should do |
| `reason` | string | Why this decision was made |
| `audit_event_id` | UUID | Immutable reference to the audit record |
| `review_id` | UUID or null | Only present when `decision == "review"` |
| `duration_ms` | integer | AIControl intercept latency |

### Reason strings

| Reason | Meaning |
|--------|---------|
| `default_allow` | No policy matched — default allow fired |
| `tool_denylisted` | Tool name is in a `tool_denylist` policy |
| `parameter_policy_violation: key=value` | A parameter-level condition matched |
| `requires_human_review` | A `tool_pattern` policy matched |

---

## Handling decisions in your agent

**allow** — proceed with tool execution as normal.

**deny** — do not execute the tool. Log the `reason` and `audit_event_id`. Surface a clear error to any downstream process. Example:

```python
if result["decision"] == "deny":
    raise PolicyViolationError(
        f"Tool '{tool_name}' blocked by policy: {result['reason']}"
    )
```

**review** — a human reviewer has been notified via Slack. The `/intercept` endpoint returns immediately — your agent does not wait. What you do next depends on your use case:

- **Proceed and flag** — treat it as an allow but surface the `review_id` to the user. Appropriate for low-stakes review workflows.
- **Pause and poll** — poll `GET /reviews/{review_id}` until status changes from `pending`. Appropriate when you need an explicit human approval before proceeding.

```python
# Polling pattern — use when you need to block on human approval
import time, httpx

def wait_for_review(review_id: str, poll_interval: int = 5, timeout: int = 300) -> str:
    start = time.time()
    while time.time() - start < timeout:
        r = httpx.get(
            f"{AICONTROL_URL}/reviews/{review_id}",
            headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
        )
        status = r.json()["status"]
        if status in ("approved", "denied"):
            return status
        time.sleep(poll_interval)
    raise TimeoutError(f"Review {review_id} not decided within {timeout}s")
```

---

## Python universal wrapper

Drop this file into your project. All framework-specific wrappers below build on it.

```python
# aicontrol.py
import os
import uuid
import httpx
from functools import wraps
from typing import Callable

AICONTROL_URL   = os.environ["AICONTROL_URL"]
AICONTROL_TOKEN = os.environ["AICONTROL_TOKEN"]
AGENT_NAME      = os.environ.get("AGENT_NAME", "unnamed-agent")
AGENT_ID        = os.environ.get("AGENT_ID", str(uuid.uuid4()))


class PolicyViolationError(Exception):
    pass


class HumanReviewRequiredError(Exception):
    def __init__(self, review_id: str):
        self.review_id = review_id
        super().__init__(f"Human review required. Review ID: {review_id}")


def intercept(
    tool_name: str,
    tool_parameters: dict,
    session_id: str,
    sequence_number: int = 1,
) -> dict:
    response = httpx.post(
        f"{AICONTROL_URL}/intercept",
        headers={"Authorization": f"Bearer {AICONTROL_TOKEN}"},
        json={
            "session_id": session_id,
            "agent_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "tool_name": tool_name,
            "tool_parameters": tool_parameters,
            "sequence_number": sequence_number,
        },
        timeout=5.0,
    )
    response.raise_for_status()
    result = response.json()

    if result["decision"] == "deny":
        raise PolicyViolationError(
            f"Tool '{tool_name}' denied: {result['reason']}"
        )
    if result["decision"] == "review":
        raise HumanReviewRequiredError(result["review_id"])

    return result  # decision == "allow"


def governed(tool_name: str):
    """Decorator — wrap any function with an AIControl intercept."""
    def decorator(func: Callable) -> Callable:
        call_count = {"n": 0}
        @wraps(func)
        def wrapper(*args, session_id: str, sequence_number: int = 1, **kwargs):
            call_count["n"] += 1
            intercept(
                tool_name=tool_name,
                tool_parameters=kwargs,
                session_id=session_id,
                sequence_number=call_count["n"],
            )
            return func(*args, session_id=session_id, **kwargs)
        return wrapper
    return decorator
```

**Usage:**

```python
from aicontrol import governed, PolicyViolationError

@governed("query_database")
def query_database(table: str, limit: int, session_id: str, sequence_number: int = 1):
    return db.query(f"SELECT * FROM {table} LIMIT {limit}")

try:
    result = query_database(table="customers", limit=100, session_id=session_id, sequence_number=3)
except PolicyViolationError as e:
    print(f"Blocked: {e}")
```

---

## Checklist: integration complete

```
✓  AIControl deployed and verify.sh passes
✓  Agent token issued and set as AICONTROL_TOKEN env var
✓  AICONTROL_URL set to your deployment URL
✓  intercept() called before every tool execution
✓  deny decision raises an error or aborts the tool call
✓  review decision handled (proceed-and-flag or poll)
✓  session_id generated once per agent run, reused across tool calls
✓  sequence_number increments with each tool call in the session
✓  First call verified — audit event visible in dashboard
```

---

## Framework-specific wrappers

For LangChain, CrewAI, AutoGen, OpenAI Agents SDK, LangGraph, Vercel AI SDK, MCP, and TypeScript/Node.js, see [Integrations](/docs/integrations).
