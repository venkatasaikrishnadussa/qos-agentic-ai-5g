from __future__ import annotations

from typing import Any, Dict

import httpx

from app.config.settings import settings
from app.schemas.policy import PolicyAction, PolicyUpdateRequest, PolicyUpdateResponse


async def push_policy(action: PolicyAction) -> PolicyUpdateResponse:
    """
    Push a policy to the PCF mock.

    - ``internal`` (default): calls the same logic as ``POST /pcf/policy/update``
      in-process. Reliable for the agent running inside the FastAPI app (no
      HTTP loopback to self required).
    - ``http``: POST to ``{PCF_BASE_URL}/pcf/policy/update`` for split deployments
      or tests that require a real HTTP hop.
    """
    request = PolicyUpdateRequest(
        request_id=action.action_id,
        action=action,
    )

    if settings.pcf_enforcement_mode == "internal":
        from app.pcf.api import apply_policy_update

        return await apply_policy_update(request)

    url = f"{settings.pcf_base_url.rstrip('/')}/pcf/policy/update"
    payload = request.model_dump()

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        return PolicyUpdateResponse(**data)


__all__ = ["push_policy"]

