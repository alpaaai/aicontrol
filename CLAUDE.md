# AIControl — Claude Instructions

## Project
Enterprise AI agent governance middleware.
Intercepts agent tool calls, enforces policy, logs everything.

## Stack
- Python 3.14, FastAPI, SQLAlchemy, PostgreSQL
- OPA (Open Policy Agent) for policy evaluation
- Streamlit for dashboard
- Slack Bolt for human review
- Docker Compose for deployment

## OS
Ubuntu WSL2 on Windows

## Key Commands
```bash
# Start stack
docker compose up -d

# Run API
uvicorn app.main:app --reload --port 8000

# Run dashboard
streamlit run dashboard/app.py

# Run tests
pytest tests/

# Reset demo data
python scripts/seed.py

# Run demo scenario
python scripts/demo_run.py

# Database migration
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Architecture Decisions
- MCP proxy is the primary integration path
- OPA evaluates all policies — no custom policy logic in Python
- Every event writes to audit_events table regardless of decision
- Policies defined in policies/policies.yaml, compiled to OPA at startup
- Self-hosted Docker Compose is the primary customer deployment

## Code Style
- Type hints on all functions
- Pydantic models for all API request/response schemas
- SQLAlchemy async where possible
- One responsibility per file
- Tests written alongside every new function

## Current Phase
V1 prototype

## Superpowers Skills Active
- writing-plans
- executing-plans
- test-driven-development
- systematic-debugging
- verification-before-completion
- finishing-a-development-branch
