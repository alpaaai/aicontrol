"""Tests for async database engine and session factory."""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


def test_engine_is_async():
    from app.models.database import engine
    assert isinstance(engine, AsyncEngine)


def test_async_session_factory_returns_session():
    import asyncio
    from app.models.database import async_session_factory
    session = async_session_factory()
    assert isinstance(session, AsyncSession)
    asyncio.run(session.close())


def test_base_has_metadata():
    from app.models.database import Base
    from sqlalchemy.orm import DeclarativeBase
    assert issubclass(Base, DeclarativeBase)
