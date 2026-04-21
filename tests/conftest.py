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
    from dotenv import load_dotenv, dotenv_values
    # Walk up from tests/ to find .env (handles git worktrees where .env lives in the main repo root)
    _start = os.path.dirname(os.path.abspath(__file__))
    _env_file = None
    _search = _start
    for _ in range(5):
        _candidate = os.path.join(_search, ".env")
        if os.path.isfile(_candidate):
            _env_file = _candidate
            break
        _search = os.path.dirname(_search)
    if _env_file:
        load_dotenv(_env_file, override=False)  # populate os.environ without overriding explicit env vars
    _db = os.environ.get("DATABASE_URL", "")
    if "@postgres:" in _db:
        os.environ["DATABASE_URL"] = _db.replace("@postgres:", "@localhost:")
    _opa = os.environ.get("OPA_URL", "")
    if _opa == "http://opa:8181":
        os.environ["OPA_URL"] = "http://localhost:8181"
    _slack = os.environ.get("SLACK_BOT_TOKEN", "")
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

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _cleanup_test_policies():
    """Session teardown: remove any test_ policies that leaked into the DB."""
    yield
    from app.models.database import async_session_factory
    async with async_session_factory() as session:
        await session.execute(text(
            "UPDATE audit_events SET policy_id = NULL, policy_name = NULL "
            "WHERE policy_id IN (SELECT id FROM policies WHERE name LIKE 'test_%')"
        ))
        await session.execute(text("DELETE FROM policies WHERE name LIKE 'test_%'"))
        await session.commit()


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
