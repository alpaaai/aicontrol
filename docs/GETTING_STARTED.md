# AIControl — Getting Started

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A Linux VM or server (Ubuntu 22.04+ recommended)
- 2 GB RAM minimum, 4 GB recommended
- Ports 8000 (API) and 8501 (dashboard) available

## Installation

```bash
git clone https://github.com/alpaaai/aicontrol.git
cd aicontrol
bash install.sh
```

The installer will:
1. Prompt for your database password, secret key, and Slack credentials
2. Pull the latest Docker images from ghcr.io
3. Run database migrations
4. Issue your first admin token

**Save the admin token — it is shown only once.**

After install, run:
```bash
bash verify.sh
```

Expected output: `6 passed, 0 failed`.

## Accessing AIControl

| Service   | URL                           |
|-----------|-------------------------------|
| Dashboard | http://localhost:8501         |
| API       | http://localhost:8000         |
| API docs  | http://localhost:8000/docs    |
| Health    | http://localhost:8000/health  |
| Debug     | http://localhost:8000/debug   |

## Registering Your First Agent

Issue an agent token for your AI agent:

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/issue_token.py \
  --role agent --desc "My first agent"
```

Configure your agent to send the token as:
```
Authorization: Bearer <token>
```

## Your First Intercept Call

```bash
curl -X POST http://localhost:8000/intercept \
  -H "Authorization: Bearer <agent-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<uuid>",
    "agent_id": "<uuid>",
    "agent_name": "my-agent",
    "tool_name": "read_file",
    "tool_parameters": {"path": "/data/report.csv"},
    "sequence_number": 1
  }'
```

Response:
```json
{
  "decision": "allow",
  "reason": "default_allow",
  "audit_event_id": "..."
}
```

## Managing Tokens

Issue tokens:
```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/issue_token.py --role agent --desc "Agent name"
```

Revoke tokens:
```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/revoke_token.py --id <token-uuid>
```

Or use the **Tokens** tab in the dashboard.

## Updating AIControl

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml pull
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api alembic upgrade head
```

## Troubleshooting

Run the diagnostic collector and share the output with support:
```bash
bash diagnose.sh
```

| Symptom | Likely cause | Fix |
|---|---|---|
| `install.sh` fails at image pull | Not logged into ghcr.io | `docker login ghcr.io` |
| API container exits immediately | Bad `DATABASE_URL` in `.env` | Check postgres hostname is `postgres` not `localhost` |
| Dashboard can't reach API | Wrong network config | Verify both compose files use `aicontrol` network |
| `verify.sh` dashboard check fails | Dashboard slow to start | Wait 15s then re-run |
| GitHub Actions build fails | `GITHUB_TOKEN` permissions | Repo Settings → Actions → Allow write permissions |
| Image not found on ghcr.io | Package visibility private | GitHub → Packages → Change visibility to public |
| `alembic upgrade head` fails in container | Migrations not copied | Check `COPY migrations/` in Dockerfile |
| Port 8000 already in use | uvicorn running locally | `pkill -f uvicorn` then restart stack |
