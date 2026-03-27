"""Sync SQLAlchemy engine for Streamlit dashboard."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

_sync_engine: Engine | None = None
_SyncSession = None


def _get_engine() -> Engine:
    """Lazily create the sync engine on first call."""
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        from app.core.config import settings
        sync_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )
        _sync_engine = create_engine(sync_url, pool_pre_ping=True, pool_size=5)
        _SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_engine


class _EngineProxy:
    """Proxy so `sync_engine.connect()` works after lazy init."""
    def connect(self):
        return _get_engine().connect()

    def __getattr__(self, name):
        return getattr(_get_engine(), name)


sync_engine = _EngineProxy()


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager yielding a sync DB session."""
    _get_engine()  # ensure initialized
    session = _SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
