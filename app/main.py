from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings as _settings
from app.core.logging import configure_logging, get_logger
from app.models.database import async_session_factory
from app.routers.debug import router as debug_router
from app.routers.intercept import router as intercept_router
from app.routers.policies import router as policies_router
from app.routers.slack_actions import router as slack_router
from app.services.policy_loader import load_all

configure_logging(env=_settings.app_env)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run policy loader on startup."""
    logger.info("aicontrol_starting")
    async with async_session_factory() as session:
        await load_all(session)
    logger.info("aicontrol_ready")
    yield
    logger.info("aicontrol_stopping")


app = FastAPI(
    title="AIControl",
    description="Enterprise AI agent governance middleware",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(debug_router)
app.include_router(intercept_router)
app.include_router(policies_router)
app.include_router(slack_router)


@app.get("/health")
async def health() -> dict:
    """Liveness check — returns ok when the app process is running."""
    return {"status": "ok", "service": "aicontrol"}
