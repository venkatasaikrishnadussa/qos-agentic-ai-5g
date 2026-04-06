from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

registry = CollectorRegistry()

decision_latency_seconds = Histogram(
    "decision_latency_seconds",
    "Latency of policy decision loop",
    registry=registry,
)
sla_violations_total = Counter(
    "sla_violations_total",
    "Total number of SLA violations observed",
    registry=registry,
)
policies_applied_total = Counter(
    "policies_applied_total",
    "Total number of policies successfully applied to PCF",
    registry=registry,
)
agent_runs_total = Counter(
    "agent_runs_total",
    "Total number of agent reasoning cycles executed",
    registry=registry,
)
agent_decisions_total = Counter(
    "agent_decisions_total",
    "Total number of agent cycles that produced a concrete policy decision",
    registry=registry,
)
agent_rewards = Histogram(
    "agent_rewards",
    "Distribution of agent reward scores",
    registry=registry,
)

metrics_router = APIRouter()


def configure_metrics() -> None:
    # Metrics objects are created at import time; nothing else required for now.
    return None


@metrics_router.get("/metrics")
async def metrics() -> Response:
    content = generate_latest(registry)
    return Response(content=content, media_type="text/plain; version=0.0.4")

