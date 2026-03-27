"""Tests for sync dashboard DB connection."""
from sqlalchemy.orm import Session
from sqlalchemy import text


def test_sync_engine_connects():
    """Sync engine must connect to Postgres and return a result."""
    from dashboard.db import sync_engine
    with sync_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_get_sync_session_returns_session():
    """get_sync_session must return a usable SQLAlchemy Session."""
    from dashboard.db import get_sync_session
    with get_sync_session() as session:
        assert isinstance(session, Session)
