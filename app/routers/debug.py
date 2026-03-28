"""GET /debug — public system health snapshot."""
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database import async_session_factory

router = APIRouter()
logger = get_logger("debug")
APP_VERSION = "0.1.0"


async def _check_database() -> dict[str, Any]:
    try:
        async with async_session_factory() as session:
            policy_count = (
                await session.execute(text("SELECT COUNT(*) FROM policies"))
            ).scalar()
            agent_count = (
                await session.execute(text("SELECT COUNT(*) FROM agents"))
            ).scalar()
            last_event = (
                await session.execute(
                    text("SELECT created_at FROM audit_events "
                         "ORDER BY created_at DESC LIMIT 1")
                )
            ).scalar()
        return {
            "status": "ok",
            "policy_count": policy_count,
            "agent_count": agent_count,
            "last_event_at": last_event.isoformat() if last_event else None,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _check_opa() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.opa_url}/health")
        return {
            "status": "ok" if response.status_code == 200 else "degraded",
            "url": settings.opa_url,
        }
    except Exception as e:
        return {"status": "error", "url": settings.opa_url, "detail": str(e)}


@router.get("/debug")
async def debug() -> dict[str, Any]:
    """System health snapshot — public, no auth required."""
    db = await _check_database()
    opa = await _check_opa()
    logger.info("debug_check", db_status=db["status"], opa_status=opa["status"])
    return {
        "version": APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "database": db,
        "opa": opa,
        "policies": db.get("policy_count"),
        "agents": db.get("agent_count"),
        "last_event": db.get("last_event_at"),
        "env": settings.app_env,
    }
