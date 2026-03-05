from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from app.schemas.common import SliceAllocation


class UPFTelemetry(BaseModel):
    upf_id: str
    throughput_mbps: float
    latency_ms: float
    packet_loss_percent: float
    utilization_percent: float


class SMFTelemetry(BaseModel):
    smf_id: str
    session_count: int
    control_plane_load_percent: float


class AMFTelemetry(BaseModel):
    amf_id: str
    signaling_load_percent: float
    registration_success_rate: float


class NwdafAnalytics(BaseModel):
    congestion_risk_score: float = Field(ge=0.0, le=1.0)
    predicted_hotspots: Dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of cell/site IDs to predicted congestion probability.",
    )


class TelemetrySnapshot(BaseModel):
    upf: UPFTelemetry
    smf: SMFTelemetry
    amf: AMFTelemetry
    nwdaf: NwdafAnalytics
    current_allocations: List[SliceAllocation]

