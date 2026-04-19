# API Reference

Base URL: `http://your-aicontrol-host:8000`

Interactive docs (Swagger UI): `http://your-aicontrol-host:8000/docs`

---

## Authentication

All endpoints require a JWT token issued by AIControl, passed as a Bearer header:

```
Authorization: Bearer <token>
```

Two roles:

| Role | Can call |
|------|---------|
| `agent` | `POST /intercept`, `GET /reviews/{id}` |
| `admin` | All endpoints |

Issue tokens with `scripts/issue_token.py` or `POST /tokens`. Tokens do not expire but can be revoked at any time.

---

## Intercept

### POST /intercept

The core integration point. Call this before executing any agent tool.

**Auth:** agent token

**Request:**

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

**Response 200:**

```json
{
  "decision": "allow",
  "reason": "default_allow",
  "audit_event_id": "3f2a1c8b-...",
  "review_id": null,
  "duration_ms": 7
}
```

`decision` is one of `allow`, `deny`, or `review`.

`review_id` is only present when `decision == "review"`. Use it to poll `GET /reviews/{review_id}`.

---

## Agents

### GET /agents

List all registered agents.

**Auth:** admin

**Response 200:** array of agent objects

---

### GET /agents/{agent_id}

Get one agent.

**Auth:** admin

**Response:** 200 with agent object, or 404

---

### POST /agents

Register a new agent.

**Auth:** admin

**Request:**

```json
{
  "name": "loan-underwriting-agent",
  "owner": "platform-team@company.com",
  "framework": "langchain",
  "model_version": "gpt-4o",
  "approved_tools": ["query_credit_bureau", "read_loan_application"],
  "system_prompt_hash": "sha256hex",
  "metadata": {}
}
```

All fields except `name` are optional.

**Response 201:**

```json
{
  "id": "7c4d2e8f-...",
  "name": "loan-underwriting-agent",
  "owner": "platform-team@company.com",
  "status": "unregistered",
  "framework": "langchain",
  "model_version": "gpt-4o",
  "approved_tools": ["query_credit_bureau", "read_loan_application"],
  "approved_by": null
}
```

---

### PUT /agents/{agent_id}

Update an agent. All fields optional.

**Auth:** admin

**Request:**

```json
{
  "status": "active",
  "approved_by": "ciso@company.com",
  "approved_tools": ["query_credit_bureau"],
  "owner": "new-team@company.com"
}
```

**Response:** 200 with updated agent object, or 404

---

### DELETE /agents/{agent_id}

Delete an agent record.

**Auth:** admin

**Response:** 204, or 404

---

### DELETE /agents/{agent_id}/token

Revoke all active tokens associated with this agent.

**Auth:** admin

**Response 200:**

```json
{ "revoked": 2 }
```

Returns 404 if no active token found.

---

## Tokens

### POST /tokens

Issue a new API token.

If `agent_id` is provided, any prior active token for that agent is automatically revoked. One active token per agent is enforced.

**Auth:** admin

**Request:**

```json
{
  "role": "agent",
  "description": "loan-underwriting-agent prod token",
  "agent_id": "7c4d2e8f-..."
}
```

`agent_id` is optional. `role` is `agent` or `admin`.

**Response 200:**

```json
{
  "token_id": "a3b1c9d2-...",
  "role": "agent",
  "description": "loan-underwriting-agent prod token",
  "agent_id": "7c4d2e8f-...",
  "token": "eyJhbGc..."
}
```

**The `token` value is shown once and not stored in plaintext. Save it immediately.**

---

## Policies

### GET /policies

List all policies.

**Auth:** admin

**Response 200:** array of policy objects

---

### GET /policies/{policy_id}

Get one policy.

**Auth:** admin

**Response:** 200 with policy object, or 404

---

### POST /policies

Create a policy. Takes effect in the policy engine immediately — no restart needed.

**Auth:** admin

**Request:**

```json
{
  "name": "block_unscoped_crm_query",
  "description": "Prevent unfiltered CRM queries",
  "rule_type": "tool_denylist",
  "condition": {
    "blocked_tools": ["query_accounts"],
    "parameter_match": { "filter": null }
  },
  "action": "deny",
  "severity": "critical",
  "compliance_frameworks": ["SOC2", "GDPR"]
}
```

`rule_type` is `tool_denylist` or `tool_pattern`. See [Policies](/docs/policies) for condition schemas.

**Response 201:** policy object with generated `id`.

---

### PUT /policies/{policy_id}

Update a policy. All fields optional. Takes effect immediately.

**Auth:** admin

**Request:**

```json
{
  "active": false,
  "severity": "high",
  "condition": { "blocked_tools": ["query_accounts", "query_all_leads"] }
}
```

**Response:** 200 with updated policy object, or 404

---

### DELETE /policies/{policy_id}

Delete a policy. Takes effect immediately.

**Auth:** admin

**Response:** 204, or 404

---

## Reviews (HITL)

### GET /reviews/{review_id}

Get the status of a human review.

Agents use this to poll for a decision after receiving `decision: review` from `/intercept`.

**Auth:** agent or admin

**Response 200:**

```json
{
  "id": "f1e2d3c4-...",
  "audit_event_id": "3f2a1c8b-...",
  "session_id": "b3e1f9a2-...",
  "status": "pending",
  "reviewer": null,
  "review_note": null,
  "reviewed_at": null,
  "created_at": "2026-04-14T10:20:00"
}
```

`status` is `pending`, `approved`, or `denied`. Once `approved` or `denied`, `reviewer` contains the Slack user ID of the reviewer and `reviewed_at` is set.

Returns 404 if the review ID does not exist.

---

### GET /reviews

List reviews. Useful for compliance dashboards and ops automation.

**Auth:** admin

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `status` | Filter by `pending`, `approved`, or `denied` |
| `limit` | Max results (default 50, max 200) |
| `offset` | Pagination offset |

**Response 200:** array of review objects

---

## Error responses

All endpoints return standard HTTP status codes.

| Code | Meaning |
|------|---------|
| 400 | Bad request — missing or invalid fields |
| 401 | Missing or invalid token |
| 403 | Token lacks permission for this endpoint |
| 404 | Resource not found |
| 422 | Validation error — response body contains field-level detail |
| 500 | Internal server error |

Error response body:

```json
{
  "detail": "Policy with this name already exists"
}
```

---

## Health check

### GET /health

Returns `200 {"status": "ok"}` when the API is running. Use this for load balancer health checks and uptime monitoring.

No authentication required.
