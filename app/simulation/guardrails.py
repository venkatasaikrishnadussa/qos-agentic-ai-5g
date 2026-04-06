from __future__ import annotations

from typing import List

from app.schemas.common import SliceAllocation
from app.schemas.policy import PolicyAction, PolicyValidationErrorDetail


class PolicyValidationError(Exception):
    def __init__(self, detail: PolicyValidationErrorDetail):
        super().__init__(detail.message)
        self.detail = detail


def _validate_total_allocation(allocations: List[SliceAllocation]) -> None:
    total = sum(a.bandwidth_percent for a in allocations)
    if abs(total - 100.0) > 1e-3:
        raise PolicyValidationError(
            PolicyValidationErrorDetail(
                message=f"Total allocation must be 100%, but was {total:.2f}%.",
                violated_constraint="TOTAL_ALLOCATION_EQUALS_100",
            )
        )


def _validate_urllc_bandwidth(allocations: List[SliceAllocation]) -> None:
    urllc = next((a for a in allocations if a.slice_type == "URLLC"), None)
    if urllc is None or urllc.bandwidth_percent < 30.0:
        raise PolicyValidationError(
            PolicyValidationErrorDetail(
                message="URLLC bandwidth must be at least 30%.",
                violated_constraint="URLLC_MIN_30_PERCENT",
            )
        )


def _validate_latency(latency_ms: float) -> None:
    if latency_ms >= 5.0:
        raise PolicyValidationError(
            PolicyValidationErrorDetail(
                message=f"Enterprise SLA latency must be <5ms, got {latency_ms:.2f}ms.",
                violated_constraint="ENTERPRISE_LATENCY_LT_5_MS",
            )
        )


def apply_action_to_allocations(
    allocations: List[SliceAllocation], action: PolicyAction
) -> List[SliceAllocation]:
    """
    Return a new allocations list reflecting the proposed action.

    The target slice is set to the requested value, and all non-target slices
    are proportionally rescaled so the total remains exactly 100%.
    """
    target_value = float(action.new_allocation_percent)

    non_target = [a for a in allocations if a.slice_type != action.target_slice]
    non_target_total = sum(a.bandwidth_percent for a in non_target)
    remaining_total = max(0.0, 100.0 - target_value)

    updated: List[SliceAllocation] = []
    for alloc in allocations:
        if alloc.slice_type == action.target_slice:
            updated.append(
                SliceAllocation(
                    slice_type=alloc.slice_type,
                    bandwidth_percent=target_value,
                )
            )
            continue

        if non_target_total <= 1e-9:
            new_percent = remaining_total / max(len(non_target), 1)
        else:
            new_percent = (alloc.bandwidth_percent / non_target_total) * remaining_total

        updated.append(
            SliceAllocation(
                slice_type=alloc.slice_type,
                bandwidth_percent=new_percent,
            )
        )

    # Correct tiny floating-point drift so total is exactly 100%.
    total = sum(a.bandwidth_percent for a in updated)
    drift = 100.0 - total
    if abs(drift) > 1e-9 and updated:
        first = updated[0]
        updated[0] = SliceAllocation(
            slice_type=first.slice_type,
            bandwidth_percent=first.bandwidth_percent + drift,
        )

    return updated


def validate_policy(
    new_allocations: List[SliceAllocation], predicted_latency_ms: float
) -> None:
    """
    Guardrail validation layer enforcing hard constraints.
    """
    _validate_total_allocation(new_allocations)
    _validate_urllc_bandwidth(new_allocations)
    _validate_latency(predicted_latency_ms)

