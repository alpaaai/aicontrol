"""Shared pytest fixtures."""
import importlib
import pytest


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
