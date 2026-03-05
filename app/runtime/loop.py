from __future__ import annotations

import asyncio
from typing import Optional

from app.observability.logging import get_logger

logger = get_logger(__name__)

_closed_loop_task: Optional[asyncio.Task[None]] = None


async def _closed_loop_runner() -> None:
    """
    Placeholder closed-loop execution.

    In the full implementation this will:
    - read telemetry
    - run the LangGraph agent
    - push policies to PCF
    - observe effects and update metrics
    """
    logger.info("closed_loop_started")
    try:
        while True:
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("closed_loop_cancelled")
        raise


async def start_closed_loop() -> None:
    global _closed_loop_task
    if _closed_loop_task is None or _closed_loop_task.done():
        _closed_loop_task = asyncio.create_task(_closed_loop_runner())


async def stop_closed_loop() -> None:
    global _closed_loop_task
    if _closed_loop_task is not None and not _closed_loop_task.done():
        _closed_loop_task.cancel()
        try:
            await _closed_loop_task
        except asyncio.CancelledError:
            pass
    _closed_loop_task = None

