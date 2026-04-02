"""Shared pytest fixtures."""
import importlib
import os
import pytest

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
