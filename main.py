from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from app.agents.agent_runner import (
    get_last_decision,
    run_agent_once,
    set_operator_intent,
    start_continuous_agent,
    stop_continuous_agent,
)
from app.config.settings import settings
from app.observability.logging import configure_logging
from app.observability.metrics import configure_metrics, metrics_router
from app.pcf.api import router as pcf_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan hook.

    We configure logging and metrics once on startup. The agent loop itself
    is controlled explicitly via the /agent/start and /agent/stop endpoints.
    """
    configure_logging()
    configure_metrics()
    yield


app = FastAPI(
    title="5G Agentic Policy Optimizer",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(pcf_router, prefix="/pcf", tags=["pcf"])
app.include_router(metrics_router, tags=["metrics"])


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": settings.service_name}


class AgentIntentPayload(BaseModel):
    intent: str


@app.post("/agent/intent")
async def set_intent(payload: AgentIntentPayload) -> Dict[str, Any]:
    intent = set_operator_intent(payload.intent)
    return {"intent": intent.model_dump()}


@app.post("/agent/run")
async def agent_run_once() -> Dict[str, Any]:
    state = await run_agent_once()
    return {
        "decision": (
            state["selected_action"].model_dump()
            if state.get("selected_action") is not None
            else None
        ),
        "reward": state.get("reward"),
        "telemetry": (
            state["telemetry"].model_dump() if "telemetry" in state else None
        ),
        "iteration": state.get("iteration"),
    }


@app.post("/agent/start")
async def agent_start() -> Dict[str, Any]:
    await start_continuous_agent()
    return {"status": "running"}


@app.post("/agent/stop")
async def agent_stop() -> Dict[str, Any]:
    await stop_continuous_agent()
    return {"status": "stopped"}


@app.get("/agent/decision")
async def agent_decision() -> Dict[str, Any]:
    return get_last_decision()


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

