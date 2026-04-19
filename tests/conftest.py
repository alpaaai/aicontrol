"""Shared pytest fixtures."""
import importlib
import os
import pytest
import pytest_asyncio
import httpx
from sqlalchemy import text

# When tests run on the host machine, Docker internal hostnames won't resolve.
# Load .env (if present) and replace Docker internal hostnames with localhost.
try:
    from dotenv import dotenv_values
    _env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    _dot = dotenv_values(_env_file)
    _db = os.environ.get("DATABASE_URL") or _dot.get("DATABASE_URL", "")
    if "@postgres:" in _db:
        os.environ["DATABASE_URL"] = _db.replace("@postgres:", "@localhost:")
    _opa = os.environ.get("OPA_URL") or _dot.get("OPA_URL", "")
    if _opa == "http://opa:8181":
        os.environ["OPA_URL"] = "http://localhost:8181"
    _slack = os.environ.get("SLACK_BOT_TOKEN") or _dot.get("SLACK_BOT_TOKEN", "")
    if not _slack or _slack == "xoxb-placeholder":
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
except Exception:
    pass  # dotenv not available or .env not found — rely on existing env


@pytest.fixture(autouse=True)
def reset_config_and_db_engine():
    """
    Reload app.core.config and reset the dashboard engine cache after each test.

    test_config.py reloads app.core.config with a fake DATABASE_URL, leaving
    the module-level settings singleton poisoned for subsequent tests. This
    fixture restores the real settings and clears the cached sync engine so
    the next test gets a fresh connection with the correct URL.
    """
    yield
    import app.core.config
    importlib.reload(app.core.config)

    import dashboard.db
    dashboard.db._sync_engine = None
    dashboard.db._SyncSession = None


# ── Integration test fixtures (live API at localhost:8001) ────────────────────

@pytest_asyncio.fixture(scope="session")
async def _seed_and_token_setup():
    """Session-scoped: seed demo agents + issue admin and agent tokens once."""
    from app.core.auth import create_token, hash_token
    from app.models.database import async_session_factory
    from scripts.seed import AGENTS

    async with async_session_factory() as session:
        # Seed demo agents (idempotent)
        for agent in AGENTS:
            await session.execute(text("""
                INSERT INTO agents (id, name, owner, status, approved_tools)
                VALUES (:id, :name, :owner, :status, CAST(:tools AS jsonb))
                ON CONFLICT (id) DO NOTHING
            """), agent)

        # Issue admin token
        admin_tok = create_token(role="admin", description="pytest-admin-fixture")
        await session.execute(text("""
            INSERT INTO api_tokens (id, token_hash, role, description, revoked)
            VALUES (gen_random_uuid(), :hash, 'admin', 'pytest-admin-fixture', false)
        """), {"hash": hash_token(admin_tok)})

        # Issue unscoped agent token (no agent_id FK so any agent_id is accepted)
        agent_tok = create_token(role="agent", description="pytest-agent-fixture")
        await session.execute(text("""
            INSERT INTO api_tokens (id, token_hash, role, description, revoked)
            VALUES (gen_random_uuid(), :hash, 'agent', 'pytest-agent-fixture', false)
        """), {"hash": hash_token(agent_tok)})

        await session.commit()

    return {"admin": admin_tok, "agent": agent_tok}


@pytest_asyncio.fixture
async def client(_seed_and_token_setup):
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=10.0) as c:
        yield c


@pytest.fixture
def admin_token(_seed_and_token_setup):
    return {"Authorization": f"Bearer {_seed_and_token_setup['admin']}"}


@pytest.fixture
def agent_token(_seed_and_token_setup):
    return {"Authorization": f"Bearer {_seed_and_token_setup['agent']}"}
