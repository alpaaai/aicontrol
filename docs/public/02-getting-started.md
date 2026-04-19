# Getting Started

This guide takes you from zero to a running AIControl instance with a verified end-to-end intercept. Estimated time: 30–45 minutes.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker Engine | 24+ |
| Docker Compose | v2+ |
| OS | Ubuntu 22.04 LTS (recommended) |
| RAM | 2 GB minimum, 4 GB recommended |
| Disk | 20 GB minimum |
| Open ports | 8000 (API), 8501 (dashboard) |

A Slack workspace is optional but required for the human review (HITL) workflow.

---

## Step 1 — Install Docker

If Docker is not already installed:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version   # confirm v2+
```

---

## Step 2 — Clone and run the installer

```bash
git clone https://github.com/alpaaai/aicontrol
cd aicontrol
bash install.sh
```

The installer will prompt for:
- A PostgreSQL password
- A secret key (32+ characters, used to sign JWT tokens)
- Slack bot token, signing secret, and channel name (optional — press Enter to skip)

It then pulls Docker images, runs database migrations, and issues your first admin token.

**Save the admin token — it is displayed once and not stored in plaintext.**

---

## Step 3 — Verify

```bash
bash verify.sh
```

Expected output:

```
PASS  Postgres accepting connections
PASS  OPA reachable
PASS  API /health returns ok
PASS  API /debug database ok
PASS  Migrations applied
PASS  Dashboard reachable

Results: 6 passed, 0 failed
All checks passed. AIControl is ready.
```

If any check fails, run `bash diagnose.sh` and send the output to hello@aictl.io.

---

## Step 4 — Access the services

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |
| Health check | http://localhost:8000/health |

---

## Step 5 — Issue an agent token

Agents authenticate with AIControl using JWT tokens scoped to the `agent` role. Issue one for your first agent:

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/issue_token.py \
  --role agent \
  --desc "my-first-agent"
```

You will see output like:

```
Token ID : a3f2...
Role     : agent
Token    : eyJhbGc...
```

Save this token. It is shown once. Set it as an environment variable for your agent:

```bash
export AICONTROL_TOKEN="eyJhbGc..."
export AICONTROL_URL="http://localhost:8000"
```

---

## Step 6 — Make your first governed call

```bash
curl -X POST http://localhost:8000/intercept \
  -H "Authorization: Bearer $AICONTROL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "11111111-1111-1111-1111-111111111111",
    "agent_id": "22222222-2222-2222-2222-222222222222",
    "agent_name": "my-first-agent",
    "tool_name": "read_file",
    "tool_parameters": {"path": "/data/report.csv"},
    "sequence_number": 1
  }'
```

Expected response:

```json
{
  "decision": "allow",
  "reason": "default_allow",
  "audit_event_id": "3f2a1c...",
  "duration_ms": 7
}
```

Now try a tool that the default `block_dangerous_tools` policy will deny:

```bash
curl -X POST http://localhost:8000/intercept \
  -H "Authorization: Bearer $AICONTROL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "11111111-1111-1111-1111-111111111111",
    "agent_id": "22222222-2222-2222-2222-222222222222",
    "agent_name": "my-first-agent",
    "tool_name": "shell_exec",
    "tool_parameters": {"command": "rm -rf /"},
    "sequence_number": 2
  }'
```

Expected response:

```json
{
  "decision": "deny",
  "reason": "tool_denylisted",
  "audit_event_id": "8c91d2...",
  "duration_ms": 6
}
```

Open the dashboard at http://localhost:8501 — both events should appear in the Audit Log tab.

---

## Default policies

Three policies are active immediately after installation:

| Policy | Type | Action |
|--------|------|--------|
| `block_dangerous_tools` | tool_denylist | deny: `execute_code`, `delete_database`, `drop_table`, `shell_exec`, `rm_rf` |
| `require_review_for_external_calls` | tool_pattern | review: tools matching `http_request`, `webhook`, `external_api` |
| `allow_standard_tools` | — | allow everything else (default) |

You can modify or delete these policies via the dashboard or the [Policies API](/docs/policies).

---

## Token management

**Issue a token:**
```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/issue_token.py --role agent --desc "agent-name"
```

**Revoke a token:**
```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/revoke_token.py --id TOKEN_UUID
```

Or use the **Tokens** tab in the dashboard.

---

## Updating AIControl

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml pull
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d
docker compose exec api alembic upgrade head
```

Migrations are backward-compatible. Running `alembic upgrade head` after each update is safe and required.

---

## Next steps

- [Integration](/docs/integration) — connect your agent to the intercept endpoint
- [Policies](/docs/policies) — create and manage governance policies
- [Operations](/docs/operations) — token lifecycle, monitoring, production notes
