# Audit Log

Every intercept call — regardless of decision — produces an immutable audit record in PostgreSQL. The record is written before the response is returned to the agent. There are no gaps in the trail.

---

## Audit event schema

The `audit_events` table. Fields a compliance engineer will care about:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Immutable event identifier |
| `session_id` | UUID | Groups all tool calls within one agent run |
| `sequence_number` | integer | Call order within the session (starts at 1) |
| `agent_id` | UUID | FK to the `agents` table |
| `agent_name` | string | Denormalized agent name — queryable without a join |
| `tool_name` | string | The tool that was called |
| `tool_parameters` | JSONB | Full parameters at time of call |
| `decision` | string | `allow`, `deny`, or `review` |
| `decision_reason` | text | Why this decision was made |
| `policy_id` | UUID | FK to the policy that fired; null on default allow |
| `policy_name` | string | Denormalized policy name — queryable without a join |
| `duration_ms` | integer | AIControl intercept latency in milliseconds |
| `created_at` | timestamp | Server-set, immutable |

`tool_parameters` is stored as JSONB — it supports indexed queries on specific parameter values.

`policy_id` and `policy_name` are null when the decision is `allow` with reason `default_allow` (no policy matched). When a policy fires, both are populated.

---

## Decision reasons

| `decision_reason` | Meaning |
|-------------------|---------|
| `default_allow` | No policy matched — default allow |
| `tool_denylisted` | Tool name matched a `tool_denylist` policy |
| `parameter_policy_violation: key=value` | A parameter-level condition matched |
| `requires_human_review` | A `tool_pattern` policy matched |

---

## Viewing the audit log

Open the **Audit Log** tab in the dashboard at `http://localhost:8501`. You can filter by agent, decision, and tool name. Each row shows the session, tool, decision, reason, policy, and latency.

For programmatic access, query the `audit_events` table directly:

```sql
-- All deny events in the last 7 days
SELECT
  created_at,
  agent_name,
  tool_name,
  tool_parameters,
  decision_reason,
  policy_name
FROM audit_events
WHERE decision = 'deny'
  AND created_at > now() - interval '7 days'
ORDER BY created_at DESC;
```

```sql
-- All events for a specific session
SELECT
  sequence_number,
  tool_name,
  tool_parameters,
  decision,
  decision_reason,
  duration_ms
FROM audit_events
WHERE session_id = 'b3e1f9a2-...'
ORDER BY sequence_number;
```

```sql
-- Deny events by policy, for SOC2 compliance export
SELECT
  ae.created_at,
  ae.agent_name,
  ae.tool_name,
  ae.tool_parameters,
  ae.decision_reason,
  p.name AS policy_name,
  p.compliance_frameworks
FROM audit_events ae
JOIN policies p ON ae.policy_id = p.id
WHERE ae.decision = 'deny'
  AND 'SOC2' = ANY(p.compliance_frameworks)
ORDER BY ae.created_at DESC;
```

---

## What is and isn't stored

**Stored in every audit event:**
- Full tool parameters as submitted by the agent (JSONB)
- The policy that fired, with its compliance framework tags
- Decision and reason
- Intercept latency

**Not stored:**
- Tool execution results — AIControl governs the call, not the response
- LLM prompt or completion content — AIControl operates at the tool layer only
- Agent-to-agent communication — only tool calls that pass through `/intercept` are recorded

---

## Immutability

Audit records are append-only. The API and dashboard have no delete or update endpoint for `audit_events`. The `created_at` timestamp is server-set and not modifiable by clients.

If you need to enforce immutability at the database level, configure your PostgreSQL user to have `INSERT`-only access to `audit_events` and remove `UPDATE`/`DELETE` grants.

---

## Retention

There is no automatic retention policy in V1. Manage retention directly in PostgreSQL:

```sql
-- Example: delete events older than 365 days (run via scheduled job)
DELETE FROM audit_events WHERE created_at < now() - interval '365 days';
```

For regulated industries, most customers retain audit events for the duration required by their applicable framework (SOC2: 1 year, GDPR: varies by purpose, HIPAA: 6 years).

---

## Backup

The audit log lives in the `aicontrol` PostgreSQL database. Back it up using standard PostgreSQL tooling:

```bash
# Dump the audit_events table
docker compose exec postgres pg_dump \
  -U aicontrol \
  -t audit_events \
  aicontrol > audit_events_$(date +%Y%m%d).sql
```

For production deployments, configure continuous WAL archiving or use a managed PostgreSQL service with automated backups.

---

## Human review records

When a tool call returns `decision: review`, a corresponding record is created in the `hitl_reviews` table. Review records link to their audit event via `audit_event_id`.

Review records are accessible via `GET /reviews` and `GET /reviews/{id}`. See [API Reference](/docs/api-reference) for the full schema.
