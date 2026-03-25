from fastapi import FastAPI

app = FastAPI(
    title="AIControl",
    description="Enterprise AI agent governance middleware",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    """Liveness check — returns ok when the app process is running."""
    return {"status": "ok", "service": "aicontrol"}
