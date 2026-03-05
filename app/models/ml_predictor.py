from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.observability.logging import get_logger
from app.schemas.telemetry import TelemetrySnapshot

logger = get_logger(__name__)


@dataclass
class CongestionPredictor:
    """
    Simple congestion predictor using a mocked scikit-learn model.

    This is intentionally minimal but pluggable, so a future RL-based
    model can be wired in behind the same interface.
    """

    model: LogisticRegression

    @classmethod
    def create_mock(cls) -> "CongestionPredictor":
        # Train a tiny mock model on synthetic data for demonstration purposes.
        X = np.array(
            [
                [40.0, 0.1],
                [60.0, 0.2],
                [70.0, 0.3],
                [80.0, 0.5],
                [90.0, 0.7],
                [95.0, 0.9],
            ]
        )  # [utilization, nwdaf_risk]
        y = np.array([0, 0, 0, 1, 1, 1])  # 0 = no congestion, 1 = congestion

        model = LogisticRegression()
        model.fit(X, y)
        logger.info("congestion_predictor_mock_trained")
        return cls(model=model)

    def _to_features(self, telemetry: TelemetrySnapshot) -> np.ndarray:
        return np.array(
            [
                [
                    telemetry.upf.utilization_percent,
                    telemetry.nwdaf.congestion_risk_score,
                ]
            ]
        )

    async def predict_congestion_probability(
        self, telemetry: TelemetrySnapshot
    ) -> float:
        features = self._to_features(telemetry)
        prob = float(self.model.predict_proba(features)[0][1])
        logger.debug(
            "congestion_prediction",
            features=features.tolist(),
            probability=prob,
        )
        return prob

    async def predict_with_metadata(
        self, telemetry: TelemetrySnapshot
    ) -> Dict[str, Any]:
        probability = await self.predict_congestion_probability(telemetry)
        return {
            "probability": probability,
            "model": "mock-logistic-regression",
        }

