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

## Known Pitfalls

### Streamlit sys.path collision with `app.py`
Streamlit adds the script's directory to `sys.path`. Because the dashboard entry point is `dashboard/app.py`, any code that does `from app.core.config import ...` (or any `from app import ...`) inside `dashboard/` will cause Python to find `dashboard/app.py` as the `app` module and re-execute it — triggering duplicate Streamlit widget errors.

**Rule**: Never import from `app.*` inside `dashboard/`. Read config values directly from environment variables (`os.environ` + `load_dotenv()`).

### Raw SQL `::jsonb` cast breaks with SQLAlchemy `text()`
`:param::jsonb` in a `text()` query fails because SQLAlchemy's parameter substitution conflicts with the `::` cast operator.

**Rule**: Use `CAST(:param AS jsonb)` instead of `:param::jsonb` in all raw SQL strings.

### UUID primary keys need explicit `gen_random_uuid()` in raw SQL INSERTs
SQLAlchemy ORM models define `server_default=func.gen_random_uuid()`, but this only applies when using the ORM. Raw `text()` INSERT statements must explicitly include `id` in the column list and `gen_random_uuid()` in VALUES.

**Rule**: Always include `id, gen_random_uuid()` in raw SQL INSERTs for tables with UUID PKs.

### SQLAlchemy echo logs in scripts — `setLevel` after engine creation doesn't work
`create_async_engine(echo=True)` sets the `sqlalchemy.engine.Engine` logger to INFO at engine creation time. Calling `logging.getLogger("sqlalchemy.engine").setLevel(WARNING)` afterwards has no effect because the child logger already has INFO set independently.

**Rule**: Never suppress logs inside the script itself (that breaks dev). If a caller (e.g. Streamlit dashboard) needs clean output, pass `APP_ENV=production` in the subprocess `env`: `env={**os.environ, "APP_ENV": "production"}`. Scripts stay unchanged and dev logging is preserved.

### OPA Rego — `decision != "deny"` is invalid for priority ordering
Using `decision != "deny"` as a guard inside another `decision` rule causes undefined behavior in Rego because rules are not evaluated sequentially — the value of `decision` is not yet known when the rule is being evaluated.

**Rule**: Use helper rules (`is_blacklisted`, `needs_review`) and `not helper_rule` to express priority ordering. Never reference `decision` inside a rule that defines `decision`.

## Superpowers Skills Active
- writing-plans
- executing-plans
- test-driven-development
- systematic-debugging
- verification-before-completion
- finishing-a-development-branch
