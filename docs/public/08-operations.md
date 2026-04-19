# Operations

Reference for running AIControl in production: token lifecycle, human review workflow, monitoring, updates, and troubleshooting.

---

## Token lifecycle

AIControl uses JWT tokens for all API authentication. Tokens do not expire but can be revoked immediately.

**Token roles:**

| Role | Permitted calls |
|------|----------------|
| `agent` | `POST /intercept`, `GET /reviews/{id}` |
| `admin` | All endpoints including policy and agent management |

**Issue a token:**

```bash
# Via CLI
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/issue_token.py \
  --role agent \
  --desc "claims-processing-agent-prod"

# Via API
curl -X POST http://localhost:8000/tokens \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "agent", "description": "claims-processing-agent-prod", "agent_id": "uuid"}'
```

The token value is returned once and not stored in plaintext. Save it to your secrets manager immediately.

**Revoke a token:**

```bash
# Via CLI
docker compose exec api python scripts/revoke_token.py --id TOKEN_UUID

# Via API — revoke all tokens for an agent
curl -X DELETE http://localhost:8000/agents/{agent_id}/token \
  -H "Authorization: Bearer <admin-token>"
```

Or use the **Tokens** tab in the dashboard.

**Token rotation:**

When you issue a new token with `agent_id` specified, any prior active token for that agent is automatically revoked. To rotate a token: issue a new one (the old one is revoked), update the environment variable in your agent's deployment, redeploy.

**One active token per agent** is enforced when `agent_id` is supplied. Tokens issued without an `agent_id` are not subject to this constraint (useful for admin scripts and automation).

---

## Human review workflow (HITL)

When a `tool_pattern` policy matches, the `/intercept` endpoint returns `decision: review` immediately. In the background, AIControl posts a Block Kit message to the configured Slack channel.

**The Slack notification contains:**
- Agent name and tool name
- The reason the review was triggered
- Full tool parameters (first 300 characters)
- A review ID (first 8 characters, for reference)
- Green **Approve** and red **Deny** buttons

**The reviewer clicks a button.** Slack sends the click to AIControl's webhook handler, which:
1. Verifies the Slack signing secret (5-minute replay window)
2. Looks up the review record by ID
3. Sets status to `approved` or `denied`
4. Records the reviewer's Slack user ID
5. Posts a confirmation message to the channel

**Important:** `/intercept` returns to the agent immediately — it does not wait for the Slack review. Your agent receives `decision: review` and a `review_id`. Whether you pause execution and poll `GET /reviews/{review_id}` or proceed is up to your integration. See [Integration](/docs/integration#handling-decisions-in-your-agent) for the polling pattern.

**Configuring Slack:**

Set these in your `.env` file before starting the stack:

```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_REVIEW_CHANNEL=#aicontrol-reviews
```

Your Slack app requires the `chat:write` scope and the Interactivity feature enabled, with the Request URL set to `http://your-host:8000/slack/actions`.

If Slack is not configured, review decisions are still created in `hitl_reviews` — they just won't have a notification path. The `GET /reviews/{id}` endpoint still works for polling.

---

## Monitoring

**Health check:**

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Use this endpoint for load balancer health checks and uptime monitoring. No authentication required.

**Structured logs:**

AIControl uses structlog for all application logging. Logs are emitted as JSON to stdout. To capture them:

```bash
docker compose logs -f api
```

Each log line includes: timestamp, log level, event name, and contextual fields (agent_id, session_id, decision, duration_ms for intercept calls).

**Dashboard:**

The Streamlit dashboard at `http://localhost:8501` shows:
- Audit log with search and filter
- Decision breakdown (allow / deny / review counts)
- Risk score trend over time
- Policy manager
- Agent registry
- Token management

---

## Updating AIControl

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml pull
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d
docker compose exec api alembic upgrade head
```

Migrations are backward-compatible. Run `alembic upgrade head` after every update.

Downtime during the `up -d` step is typically under 5 seconds. For zero-downtime updates, place a load balancer in front of the API container and perform a rolling restart.

---

## Backup

**Database backup:**

```bash
# Full database dump
docker compose exec postgres pg_dump \
  -U aicontrol aicontrol > aicontrol_$(date +%Y%m%d).sql

# Audit events only
docker compose exec postgres pg_dump \
  -U aicontrol -t audit_events aicontrol > audit_events_$(date +%Y%m%d).sql
```

For production, use a managed PostgreSQL service with automated backups, or configure WAL archiving. The `audit_events` table is append-only and will grow continuously — plan storage accordingly.

**Policy backup:**

Policies live in the `policies` table. They are included in a full database dump. You can also export them via the API:

```bash
curl http://localhost:8000/policies \
  -H "Authorization: Bearer <admin-token>" | jq . > policies_backup.json
```

---

## Deployment topology

AIControl V1 runs as a single-node Docker Compose stack. This is the supported production topology today.

Four containers:

| Container | Purpose | Notes |
|-----------|---------|-------|
| `api` | FastAPI governance API | Stateless; can be scaled horizontally behind a load balancer |
| `opa` | Policy evaluation | Sidecar to the API; runs on the same host |
| `postgres` | Audit store | State lives here; back up and monitor |
| `dashboard` | Streamlit | Internal ops tool; does not need to be internet-accessible |

Horizontal scaling of the `api` container is possible with a shared PostgreSQL instance and a load balancer, but OPA is currently configured as a per-host sidecar. Multi-node and Kubernetes support is on the roadmap.

For high-availability requirements today, deploy on a host with sufficient resources (4 cores, 4GB RAM recommended) and configure PostgreSQL with a managed service rather than the bundled container.

---

## Troubleshooting

**verify.sh fails:**

```bash
bash diagnose.sh
```

Send the output to hello@aictl.io.

**OPA not reachable:**

```bash
docker compose ps          # confirm opa container is running
docker compose logs opa    # check for startup errors
curl http://localhost:8181/health  # should return {"status": "ok"}
```

**Migrations not applied:**

```bash
docker compose exec api alembic current    # show current revision
docker compose exec api alembic upgrade head
```

**Token rejected (401):**
- Confirm the token was issued for the `agent` role for `/intercept` calls
- Confirm the token has not been revoked (check the Tokens tab in the dashboard)
- Confirm `Authorization: Bearer <token>` header is present with no extra whitespace

**Dashboard not loading:**
```bash
docker compose logs dashboard    # check for Python errors
docker compose restart dashboard
```

**Support:** hello@aictl.io
