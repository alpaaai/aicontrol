"""Sync SQLAlchemy engine for Streamlit dashboard."""
import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

_sync_engine: Engine | None = None
_SyncSession = None


def _get_engine() -> Engine:
    """Lazily create the sync engine on first call."""
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        database_url = os.environ["DATABASE_URL"]
        sync_url = database_url.replace(
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
