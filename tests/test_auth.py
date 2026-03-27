"""Tests for JWT sign/verify logic."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def test_create_token_returns_string():
    """create_token must return a non-empty string."""
    from app.core.auth import create_token
    token = create_token(role="agent", description="test")
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_token_different_each_time():
    """Two tokens with same role must be different (unique jti)."""
    from app.core.auth import create_token
    t1 = create_token(role="agent", description="a")
    t2 = create_token(role="agent", description="b")
    assert t1 != t2


def test_decode_token_returns_payload():
    """decode_token must return payload with role and jti."""
    from app.core.auth import create_token, decode_token
    token = create_token(role="admin", description="test")
    payload = decode_token(token)
    assert payload["role"] == "admin"
    assert "jti" in payload


def test_decode_token_invalid_raises():
    """decode_token must raise on invalid token."""
    from app.core.auth import decode_token
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_hash_token_is_deterministic():
    """Same token string must always produce same hash."""
    from app.core.auth import hash_token
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_different_inputs():
    """Different tokens must produce different hashes."""
    from app.core.auth import hash_token
    assert hash_token("abc") != hash_token("def")
