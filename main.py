from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import settings
from app.observability.logging import configure_logging
from app.observability.metrics import configure_metrics, metrics_router
from app.pcf.api import router as pcf_router
from app.runtime.loop import start_closed_loop, stop_closed_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    configure_metrics()
    await start_closed_loop()
    try:
        yield
    finally:
        await stop_closed_loop()


app = FastAPI(
    title="5G Agentic Policy Optimizer",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(pcf_router, prefix="/pcf", tags=["pcf"])
app.include_router(metrics_router, tags=["metrics"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


def run() -> None:
    """Entrypoint for `python main.py` if desired."""
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()

