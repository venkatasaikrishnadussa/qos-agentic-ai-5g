from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.common import RewardMetrics, SliceAllocation


class PolicyAction(BaseModel):
    action_id: str
    description: str
    target_slice: Literal["eMBB", "URLLC", "mMTC", "ENTERPRISE"]
    new_allocation_percent: float = Field(ge=0.0, le=100.0)


class PolicyDecision(BaseModel):
    selected_action: PolicyAction
    reward: RewardMetrics
    reason: str


class PolicyUpdateRequest(BaseModel):
    request_id: str
    action: PolicyAction


class PolicyUpdateResponse(BaseModel):
    status: Literal["applied", "rejected"]
    reason: Optional[str] = None
    applied_action: Optional[PolicyAction] = None


class PolicyValidationErrorDetail(BaseModel):
    message: str
    violated_constraint: str


class StoredPolicy(BaseModel):
    policy_id: str
    action: PolicyAction
    applied_at: str
    allocations: list[SliceAllocation]

