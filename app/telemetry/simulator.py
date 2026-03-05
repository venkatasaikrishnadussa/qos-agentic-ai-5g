from __future__ import annotations

import asyncio
import random
from typing import AsyncGenerator

from app.observability.logging import get_logger
from app.schemas.common import SliceAllocation
from app.schemas.telemetry import (
    AMFTelemetry,
    NwdafAnalytics,
    SMFTelemetry,
    TelemetrySnapshot,
    UPFTelemetry,
)

logger = get_logger(__name__)


async def telemetry_stream(
    interval_seconds: float = 1.0,
) -> AsyncGenerator[TelemetrySnapshot, None]:
    """
    Async generator that yields simulated telemetry snapshots for UPF, SMF, AMF and NWDAF.
    Includes a simple congestion prediction output as part of NWDAF analytics.
    """
    upf_id = "upf-1"
    smf_id = "smf-1"
    amf_id = "amf-1"

    while True:
        base_utilization = random.uniform(40.0, 95.0)
        congestion_risk = max(0.0, min(1.0, (base_utilization - 60.0) / 40.0))

        upf = UPFTelemetry(
            upf_id=upf_id,
            throughput_mbps=random.uniform(1000.0, 10000.0),
            latency_ms=random.uniform(1.0, 15.0),
            packet_loss_percent=random.uniform(0.0, 2.0),
            utilization_percent=base_utilization,
        )

        smf = SMFTelemetry(
            smf_id=smf_id,
            session_count=random.randint(10000, 200000),
            control_plane_load_percent=random.uniform(20.0, 85.0),
        )

        amf = AMFTelemetry(
            amf_id=amf_id,
            signaling_load_percent=random.uniform(10.0, 80.0),
            registration_success_rate=random.uniform(98.0, 99.999),
        )

        nwdaf = NwdafAnalytics(
            congestion_risk_score=congestion_risk,
            predicted_hotspots={"cell-1": congestion_risk, "cell-2": congestion_risk * 0.8},
        )

        # Simple baseline allocations
        current_allocations = [
            SliceAllocation(slice_type="URLLC", bandwidth_percent=30.0),
            SliceAllocation(slice_type="eMBB", bandwidth_percent=50.0),
            SliceAllocation(slice_type="mMTC", bandwidth_percent=10.0),
            SliceAllocation(slice_type="ENTERPRISE", bandwidth_percent=10.0),
        ]

        snapshot = TelemetrySnapshot(
            upf=upf, smf=smf, amf=amf, nwdaf=nwdaf, current_allocations=current_allocations
        )

        logger.debug("generated_telemetry", snapshot=snapshot.model_dump())
        yield snapshot

        await asyncio.sleep(interval_seconds)

