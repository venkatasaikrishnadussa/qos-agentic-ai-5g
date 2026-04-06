from __future__ import annotations

from app.schemas.common import RewardMetrics


def compute_reward(metrics: RewardMetrics, intent_text: str | None) -> float:
    """
    Compute a scalar reward for a simulated outcome.

    Base signal:
    - Start from the simulation's own reward_score (utilization vs SLA).
    Intent shaping:
    - "maximize utilization": up-weight utilization.
    - "protect urllc": penalize SLA violations more harshly.
    - "enterprise sla": penalize SLA violations and low latency more heavily.
    """
    intent_lower = (intent_text or "").lower()

    reward = metrics.reward_score

    # Encourage higher utilization when asked to maximize it.
    if "maximize utilization" in intent_lower:
        reward += 0.5 * metrics.predicted_utilization_percent

    # Extra penalty if SLA is violated and the operator cares about specific SLAs.
    if metrics.sla_violated:
        penalty = 100.0
        if "protect urllc" in intent_lower:
            penalty += 50.0
        if "enterprise sla" in intent_lower:
            penalty += 50.0
        reward -= penalty

    return reward

