"""Tests that tenant_id exists and is indexed on all tables."""
import pytest

TABLES = [
    "agents", "sessions", "policies",
    "audit_events", "hitl_reviews", "api_tokens",
]


@pytest.mark.parametrize("table", TABLES)
def test_tenant_id_column_exists(table):
    """tenant_id column must exist on every table."""
    from sqlalchemy import inspect, create_engine
    from app.core.config import settings
    sync_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )
    engine = create_engine(sync_url)
    cols = [c["name"] for c in inspect(engine).get_columns(table)]
    assert "tenant_id" in cols, f"{table} missing tenant_id column"


@pytest.mark.parametrize("table", TABLES)
def test_tenant_id_is_indexed(table):
    """tenant_id must have an index on every table."""
    from sqlalchemy import inspect, create_engine
    from app.core.config import settings
    sync_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )
    engine = create_engine(sync_url)
    indexes = inspect(engine).get_indexes(table)
    indexed_cols = [col for idx in indexes for col in idx["column_names"]]
    assert "tenant_id" in indexed_cols, f"{table} tenant_id missing index"
