from __future__ import annotations

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict

from app.schemas.common import OperatorIntent, RewardMetrics
from app.schemas.policy import PolicyAction
from app.schemas.telemetry import TelemetrySnapshot


class AgentState(TypedDict, total=False):
    """
    Shared state object for the LangGraph agent.

    All keys are optional at the type level, but nodes are responsible for
    setting the fields they own before downstream nodes rely on them.
    """

    telemetry: TelemetrySnapshot
    predicted_congestion: Dict[str, Any]
    candidate_actions: List[PolicyAction]
    simulated_outcomes: List[Dict[str, Any]]
    selected_action: Optional[PolicyAction]
    reward: Optional[float]
    reward_metrics: Optional[RewardMetrics]
    operator_intent: Optional[OperatorIntent]
    iteration: int

