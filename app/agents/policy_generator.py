from __future__ import annotations

from typing import List

from app.schemas.common import SliceAllocation
from app.schemas.policy import PolicyAction
from app.schemas.telemetry import TelemetrySnapshot


def _default_allocation_for_slice(
    allocations: list[SliceAllocation], slice_type: str
) -> float:
    for alloc in allocations:
        if alloc.slice_type == slice_type:
            return alloc.bandwidth_percent
    # Fallback if slice not present; this should not normally happen.
    return 0.0


def generate_candidate_actions(
    telemetry: TelemetrySnapshot,
    intent_text: str | None,
) -> List[PolicyAction]:
    """
    Generate a small set of candidate policy actions.

    This is intentionally rule-based but structured so that an LLM-backed
    generator can be plugged in later behind the same interface.
    """
    intent_lower = (intent_text or "").lower()
    current_allocations = telemetry.current_allocations

    actions: List[PolicyAction] = []

    # Baseline: react to high utilization by boosting eMBB.
    embb_current = _default_allocation_for_slice(current_allocations, "eMBB")
    if telemetry.upf.utilization_percent > 75.0:
        actions.append(
            PolicyAction(
                action_id="increase-embb",
                description="Increase eMBB bandwidth to relieve congestion",
                target_slice="eMBB",
                new_allocation_percent=min(embb_current + 5.0, 80.0),
            )
        )

    # Protect URLLC when latency-sensitive or URLLC-protection intent.
    urllc_current = _default_allocation_for_slice(current_allocations, "URLLC")
    if "protect urllc" in intent_lower or telemetry.upf.latency_ms > 4.0:
        actions.append(
            PolicyAction(
                action_id="boost-urllc",
                description="Boost URLLC slice to protect low latency traffic",
                target_slice="URLLC",
                new_allocation_percent=max(urllc_current + 5.0, 30.0),
            )
        )

    # Enterprise SLA protection.
    if "enterprise sla" in intent_lower:
        enterprise_current = _default_allocation_for_slice(
            current_allocations, "ENTERPRISE"
        )
        actions.append(
            PolicyAction(
                action_id="reserve-enterprise",
                description="Reserve additional capacity for enterprise slice to protect SLA",
                target_slice="ENTERPRISE",
                new_allocation_percent=min(enterprise_current + 5.0, 40.0),
            )
        )

    # Fallback actions to ensure at least two candidates for comparison.
    if not actions:
        # Mild rebalancing towards higher utilization.
        actions.append(
            PolicyAction(
                action_id="rebalance-embb-up",
                description="Slightly increase eMBB allocation for better utilization",
                target_slice="eMBB",
                new_allocation_percent=min(embb_current + 3.0, 70.0),
            )
        )
        actions.append(
            PolicyAction(
                action_id="rebalance-embb-down",
                description="Slightly decrease eMBB allocation to protect URLLC",
                target_slice="eMBB",
                new_allocation_percent=max(embb_current - 3.0, 20.0),
            )
        )

    return actions

