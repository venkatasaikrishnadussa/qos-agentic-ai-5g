from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from app.agents.graph import get_compiled_graph
from app.agents.state import AgentState
from app.observability.logging import get_logger
from app.observability.metrics import (
    agent_decisions_total,
    agent_runs_total,
    agent_rewards,
    decision_latency_seconds,
)
from app.schemas.common import OperatorIntent

logger = get_logger(__name__)

_last_state: Optional[AgentState] = None
_current_intent: Optional[OperatorIntent] = None
_iteration_counter: int = 0
_continuous_task: Optional[asyncio.Task[None]] = None


def set_operator_intent(text: str) -> OperatorIntent:
    """
    Store the operator intent that should guide future decisions.
    """
    global _current_intent
    _current_intent = OperatorIntent(intent_text=text, target_sla_percent=99.9)
    logger.info("agent_intent_set", intent=_current_intent.model_dump())
    return _current_intent


def get_last_decision() -> Dict[str, Any]:
    """
    Return a summary of the last agent decision for inspection.
    """
    state = _last_state or {}
    return {
        "iteration": state.get("iteration"),
        "telemetry": (
            state["telemetry"].model_dump() if "telemetry" in state else None
        ),
        "selected_action": (
            state["selected_action"].model_dump()
            if state.get("selected_action") is not None
            else None
        ),
        "reward": state.get("reward"),
        "simulated_outcomes": [
            {
                "action": o["action"].model_dump(),
                "metrics": o["metrics"].model_dump(),
            }
            for o in state.get("simulated_outcomes", [])
        ],
        "predicted_congestion": state.get("predicted_congestion"),
        "operator_intent": (
            state["operator_intent"].model_dump()
            if state.get("operator_intent") is not None
            else None
        ),
    }


async def run_agent_once() -> AgentState:
    """
    Execute a single reasoning cycle of the agent graph.
    """
    global _last_state, _iteration_counter

    _iteration_counter += 1
    initial_state: AgentState = {
        "iteration": _iteration_counter,
    }
    if _current_intent is not None:
        initial_state["operator_intent"] = _current_intent

    compiled = get_compiled_graph()

    start = time.perf_counter()
    result_state: AgentState = await compiled.ainvoke(initial_state)
    elapsed = time.perf_counter() - start

    decision_latency_seconds.observe(elapsed)
    agent_runs_total.inc()
    if result_state.get("selected_action") is not None:
        agent_decisions_total.inc()
    if result_state.get("reward") is not None:
        agent_rewards.observe(float(result_state["reward"]))  # type: ignore[arg-type]

    _last_state = result_state

    logger.info(
        "agent_cycle_completed",
        iteration=_iteration_counter,
        reward=result_state.get("reward"),
    )

    return result_state


async def _continuous_runner(interval_seconds: float) -> None:
    """
    Background loop that continuously runs the agent at a fixed cadence.
    """
    logger.info("agent_continuous_loop_started", interval_seconds=interval_seconds)
    try:
        while True:
            try:
                await run_agent_once()
            except Exception as exc:
                # Avoid "Task exception was never retrieved" and keep the loop alive.
                logger.error(
                    "agent_cycle_failed",
                    error=str(exc),
                    exc_info=True,
                )
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("agent_continuous_loop_cancelled")
        raise


async def start_continuous_agent(interval_seconds: float = 2.0) -> None:
    """
    Start the continuous agent loop if it is not already running.
    """
    global _continuous_task
    if _continuous_task is None or _continuous_task.done():
        _continuous_task = asyncio.create_task(_continuous_runner(interval_seconds))


async def stop_continuous_agent() -> None:
    """
    Stop the continuous agent loop if running.
    """
    global _continuous_task
    if _continuous_task is not None and not _continuous_task.done():
        _continuous_task.cancel()
        try:
            await _continuous_task
        except asyncio.CancelledError:
            pass
    _continuous_task = None

