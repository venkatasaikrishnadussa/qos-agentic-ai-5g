from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter

from app.observability.logging import get_logger
from app.observability.metrics import policies_applied_total
from app.schemas.policy import (
    PolicyUpdateRequest,
    PolicyUpdateResponse,
    StoredPolicy,
)

router = APIRouter()
logger = get_logger(__name__)

_POLICY_STORE: list[StoredPolicy] = []


async def apply_policy_update(request: PolicyUpdateRequest) -> PolicyUpdateResponse:
    """
    Core PCF enforcement: persist policy, metrics, structured log.

    Used by the REST route and by the agent client in ``internal`` mode so
    enforcement does not depend on HTTP loopback (avoids ConnectError in
    background tasks when the server URL/port does not match).
    """
    applied_at = datetime.now(timezone.utc).isoformat()

    stored = StoredPolicy(
        policy_id=request.request_id,
        action=request.action,
        applied_at=applied_at,
        allocations=[],
    )
    _POLICY_STORE.append(stored)
    policies_applied_total.inc()

    logger.info(
        "pcf_policy_applied",
        request_id=request.request_id,
        action=request.action.model_dump(),
    )

    return PolicyUpdateResponse(
        status="applied",
        reason=None,
        applied_action=request.action,
    )


@router.post("/policy/update", response_model=PolicyUpdateResponse)
async def update_policy(request: PolicyUpdateRequest) -> PolicyUpdateResponse:
    """
    Mock PCF endpoint that stores the applied policy and logs enforcement.
    """
    return await apply_policy_update(request)


@router.get("/policy", response_model=List[StoredPolicy])
async def list_policies() -> list[StoredPolicy]:
    """
    Return all stored policies for debugging and testing.
    """
    return list(_POLICY_STORE)

