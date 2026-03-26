from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models.database import async_session_factory
from app.routers.intercept import router as intercept_router
from app.services.policy_loader import load_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run policy loader on startup."""
    async with async_session_factory() as session:
        await load_all(session)
    yield


app = FastAPI(
    title="AIControl",
    description="Enterprise AI agent governance middleware",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(intercept_router)


@app.get("/health")
async def health() -> dict:
    """Liveness check — returns ok when the app process is running."""
    return {"status": "ok", "service": "aicontrol"}
