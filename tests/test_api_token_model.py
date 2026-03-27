"""Tests for APIToken ORM model."""
from sqlalchemy import inspect as sa_inspect


def _cols(model):
    return {c.key: c for c in sa_inspect(model).columns}


def test_api_token_table_name():
    from app.models.schemas import APIToken
    assert APIToken.__tablename__ == "api_tokens"


def test_api_token_required_columns():
    from app.models.schemas import APIToken
    cols = _cols(APIToken)
    for name in ["id", "token_hash", "role", "description", "revoked", "created_at"]:
        assert name in cols, f"api_tokens missing column: {name}"


def test_api_token_role_values():
    """Role column must exist and be a string type."""
    from app.models.schemas import APIToken
    from sqlalchemy import String
    cols = _cols(APIToken)
    assert isinstance(cols["role"].type, String)
