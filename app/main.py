from fastapi import FastAPI

from app.routers.intercept import router as intercept_router

app = FastAPI(
    title="AIControl",
    description="Enterprise AI agent governance middleware",
    version="0.1.0",
)

app.include_router(intercept_router)


@app.get("/health")
async def health() -> dict:
    """Liveness check — returns ok when the app process is running."""
    return {"status": "ok", "service": "aicontrol"}
