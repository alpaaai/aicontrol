"""JWT authentication — sign, verify, revocation check, FastAPI dependencies."""
import hashlib
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import get_db
from app.models.schemas import APIToken

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer()


def hash_token(token: str) -> str:
    """SHA-256 hash of a token string for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(role: str, description: str) -> str:
    """Issue a new non-expiring JWT with a unique jti."""
    payload = {
        "jti": str(uuid.uuid4()),
        "role": role,
        "description": description,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify JWT signature. Raises JWTError if invalid."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


async def _get_verified_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify JWT signature and check revocation. Returns payload."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
        )

    token_hash = hash_token(token)
    result = await db.execute(
        select(APIToken).where(
            APIToken.token_hash == token_hash,
            APIToken.revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found or revoked",
        )
    return payload


async def require_agent(payload: dict = Depends(_get_verified_token)) -> dict:
    """Dependency: requires agent or admin role."""
    if payload.get("role") not in ("agent", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent or admin role required",
        )
    return payload


async def require_admin(payload: dict = Depends(_get_verified_token)) -> dict:
    """Dependency: requires admin role only."""
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return payload
