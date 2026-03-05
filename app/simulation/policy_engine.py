from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from app.observability.logging import get_logger
from app.schemas.common import RewardMetrics, SliceAllocation
from app.schemas.policy import PolicyAction
from app.schemas.telemetry import TelemetrySnapshot
from app.simulation.guardrails import (
    apply_action_to_allocations,
    validate_policy,
)

logger = get_logger(__name__)


@dataclass
class PolicySimulationEngine:
    """
    Simulate the effect of a policy change on latency, utilization and SLA.
    """

    async def simulate(
        self, telemetry: TelemetrySnapshot, action: PolicyAction
    ) -> Tuple[RewardMetrics, list[SliceAllocation]]:
        # Apply the allocation change.
        new_allocations = apply_action_to_allocations(
            telemetry.current_allocations, action
        )

        # Simple heuristic simulation:
        # - Lower utilization by a small factor when bandwidth to target slice increases.
        # - Latency decreases slightly when utilization drops.
        base_util = telemetry.upf.utilization_percent
        delta = (
            action.new_allocation_percent
            - next(
                a.bandwidth_percent
                for a in telemetry.current_allocations
                if a.slice_type == action.target_slice
            )
        )

        adjusted_util = max(0.0, min(100.0, base_util - 0.2 * delta))
        predicted_latency_ms = max(
            0.5, telemetry.upf.latency_ms * (adjusted_util / max(base_util, 1e-3))
        )
        sla_violated = predicted_latency_ms >= 5.0

        # Reward: higher utilization is good, SLA violations are very bad.
        reward = adjusted_util - (100.0 if sla_violated else 0.0)

        metrics = RewardMetrics(
            predicted_latency_ms=predicted_latency_ms,
            predicted_utilization_percent=adjusted_util,
            sla_violated=sla_violated,
            reward_score=reward,
        )

        # Guardrail validation; may raise PolicyValidationError.
        validate_policy(new_allocations, predicted_latency_ms)

        logger.debug(
            "policy_simulation",
            action=action.model_dump(),
            reward=metrics.model_dump(),
        )
        return metrics, new_allocations

