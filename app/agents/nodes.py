from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.policy_generator import generate_candidate_actions
from app.agents.reward import compute_reward
from app.agents.state import AgentState
from app.models.ml_predictor import CongestionPredictor
from app.observability.logging import get_logger
from app.observability.metrics import sla_violations_total
from app.pcf.client import push_policy
from app.schemas.common import OperatorIntent, RewardMetrics
from app.schemas.policy import PolicyAction
from app.simulation.guardrails import PolicyValidationError
from app.simulation.policy_simulator import PolicySimulationEngine
from app.telemetry.simulator import telemetry_stream

logger = get_logger(__name__)

_predictor: Optional[CongestionPredictor] = None
_simulation_engine: Optional[PolicySimulationEngine] = None


def _get_predictor() -> CongestionPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CongestionPredictor.create_mock()
    return _predictor


def _get_simulation_engine() -> PolicySimulationEngine:
    global _simulation_engine
    if _simulation_engine is None:
        _simulation_engine = PolicySimulationEngine()
    return _simulation_engine


async def telemetry_node(state: AgentState) -> AgentState:
    """
    Pull a single snapshot of simulated telemetry from the 5G core.
    """
    stream = telemetry_stream(interval_seconds=0.0)
    snapshot = await stream.__anext__()  # get the next telemetry sample

    logger.info("agent_telemetry_observed", telemetry=snapshot.model_dump())

    state["telemetry"] = snapshot
    return state


async def prediction_node(state: AgentState) -> AgentState:
    """
    Use the congestion predictor to estimate near-future congestion risk.
    """
    telemetry = state["telemetry"]
    predictor = _get_predictor()
    probability = await predictor.predict_congestion_probability(telemetry)

    predicted = {
        "probability": probability,
        "source": "mock-logistic-regression",
    }

    logger.info("agent_congestion_predicted", predicted_congestion=predicted)

    state["predicted_congestion"] = predicted
    return state


async def policy_generation_node(state: AgentState) -> AgentState:
    """
    Propose a set of candidate policy actions based on telemetry and intent.
    """
    telemetry = state["telemetry"]
    intent: Optional[OperatorIntent] = state.get("operator_intent")
    intent_text = intent.intent_text if intent is not None else None

    actions = generate_candidate_actions(telemetry, intent_text)

    logger.info(
        "agent_candidate_actions_generated",
        candidate_actions=[a.model_dump() for a in actions],
        intent=intent_text,
    )

    state["candidate_actions"] = actions
    return state


async def simulation_node(state: AgentState) -> AgentState:
    """
    Simulate each candidate action and evaluate its impact on SLA and utilization.
    """
    telemetry = state["telemetry"]
    actions: List[PolicyAction] = state["candidate_actions"]

    engine = _get_simulation_engine()
    outcomes: List[Dict[str, Any]] = []

    for action in actions:
        try:
            metrics, allocations = await engine.simulate(telemetry, action)
            outcome = {
                "action": action,
                "metrics": metrics,
                "allocations": allocations,
            }
            outcomes.append(outcome)
        except PolicyValidationError as exc:
            # Keep the loop resilient: invalid candidates are rejected, not fatal.
            logger.warning(
                "agent_candidate_rejected_by_guardrails",
                action=action.model_dump(),
                reason=exc.detail.model_dump(),
            )

    logger.info(
        "agent_simulations_completed",
        outcomes=[
            {
                "action": o["action"].model_dump(),
                "metrics": o["metrics"].model_dump(),
            }
            for o in outcomes
        ],
    )

    state["simulated_outcomes"] = outcomes
    return state


async def decision_node(state: AgentState) -> AgentState:
    """
    Select the best policy action based on simulated outcomes and operator intent.

    Preference order:
    1. Avoid SLA violations.
    2. Maximize reward (which already bakes in utilization and SLA penalties).
    3. Respect operator intent via the reward shaping function.
    """
    outcomes: List[Dict[str, Any]] = state["simulated_outcomes"]
    intent: Optional[OperatorIntent] = state.get("operator_intent")
    intent_text = intent.intent_text if intent is not None else None

    best_action: Optional[PolicyAction] = None
    best_metrics: Optional[RewardMetrics] = None
    best_reward: Optional[float] = None

    for outcome in outcomes:
        metrics: RewardMetrics = outcome["metrics"]
        action: PolicyAction = outcome["action"]

        reward = compute_reward(metrics, intent_text)

        # Prefer non-SLA-violating actions first.
        sla_ok = not metrics.sla_violated
        best_sla_ok = best_metrics is not None and not best_metrics.sla_violated

        if best_action is None:
            best_action = action
            best_metrics = metrics
            best_reward = reward
            continue

        if sla_ok and not best_sla_ok:
            best_action = action
            best_metrics = metrics
            best_reward = reward
            continue

        if sla_ok == best_sla_ok and reward > (best_reward or float("-inf")):
            best_action = action
            best_metrics = metrics
            best_reward = reward

    if best_action is None or best_metrics is None:
        # This should not happen, but we guard against empty outcome lists.
        logger.warning("agent_no_valid_decision", outcomes_count=len(outcomes))
        state["selected_action"] = None
        state["reward_metrics"] = None
        return state

    logger.info(
        "agent_decision_made",
        selected_action=best_action.model_dump(),
        reward_metrics=best_metrics.model_dump(),
        reward=best_reward,
    )

    state["selected_action"] = best_action
    state["reward_metrics"] = best_metrics
    return state


async def enforcement_node(state: AgentState) -> AgentState:
    """
    Enforce the selected policy via the PCF client.

    The agent is not allowed to mutate PCF directly; it must always go through
    the PCF client which talks to the FastAPI boundary.
    """
    action: Optional[PolicyAction] = state.get("selected_action")

    if action is None:
        logger.warning("agent_enforcement_skipped_no_action")
        return state

    response = await push_policy(action)

    logger.info(
        "agent_policy_enforced",
        status=response.status,
        applied_action=(
            response.applied_action.model_dump()
            if response.applied_action is not None
            else None
        ),
    )

    return state


async def reward_node(state: AgentState) -> AgentState:
    """
    Compute and record the scalar reward for the selected outcome.
    """
    metrics: Optional[RewardMetrics] = state.get("reward_metrics")

    if metrics is None:
        state["reward"] = None
        return state

    if metrics.sla_violated:
        sla_violations_total.inc()

    intent: Optional[OperatorIntent] = state.get("operator_intent")
    intent_text = intent.intent_text if intent is not None else None

    reward_value = compute_reward(metrics, intent_text)

    logger.info(
        "agent_reward_computed",
        reward=reward_value,
        metrics=metrics.model_dump(),
        intent=intent_text,
    )

    state["reward"] = reward_value
    return state

