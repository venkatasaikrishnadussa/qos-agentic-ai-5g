from __future__ import annotations

"""
Thin wrapper around the core PolicySimulationEngine.

This provides a stable import location (`app.simulation.policy_simulator`)
for the agent layer while delegating to the existing implementation in
`policy_engine.py`.
"""

from app.simulation.policy_engine import PolicySimulationEngine

__all__ = ["PolicySimulationEngine"]

