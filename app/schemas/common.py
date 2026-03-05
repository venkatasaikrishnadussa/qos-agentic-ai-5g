from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BaseModelWithTs(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)


SliceType = Literal["eMBB", "URLLC", "mMTC", "ENTERPRISE"]


class SliceAllocation(BaseModel):
    slice_type: SliceType
    bandwidth_percent: float = Field(ge=0.0, le=100.0)


class RewardMetrics(BaseModel):
    predicted_latency_ms: float
    predicted_utilization_percent: float
    sla_violated: bool
    reward_score: float


class OperatorIntent(BaseModelWithTs):
    intent_text: str
    target_sla_percent: float = Field(ge=0.0, le=100.0)
    maximize_metric: Literal["utilization", "throughput", "revenue"] = "utilization"


class ErrorResponse(BaseModel):
    error: str
    details: Optional[dict] = None

