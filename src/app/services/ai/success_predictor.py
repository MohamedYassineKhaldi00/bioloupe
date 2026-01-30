"""Success prediction service for variant ranking."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class SuccessPredictor:
    """Predict success probability of sequence variants."""

    def calculate_success_score(
        self,
        similar_sequences: list[dict[str, Any]],
        target_property: str,
    ) -> tuple[float, float]:
        """
        Calculate success probability using weighted similarity.

        Returns: (success_score, confidence)
        """
        if not similar_sequences:
            return 0.5, 0.0

        total_weight = 0.0
        weighted_success = 0.0

        for seq in similar_sequences:
            similarity = seq["score"]
            outcome = seq["payload"]["metadata"]["outcomes"].get(target_property)

            if outcome is None:
                continue

            normalized_outcome = self._normalize_outcome(outcome, target_property)
            weight = similarity ** 2

            weighted_success += normalized_outcome * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5, 0.0

        success_score = weighted_success / total_weight
        confidence = self._calculate_confidence(
            total_weight, len(similar_sequences)
        )

        return success_score, confidence

    def _normalize_outcome(self, outcome: Any, property_type: str) -> float:
        """Normalize different outcome types to 0-1 scale."""
        if property_type == "thermostability":
            return min(1.0, max(0.0, (float(outcome) - 30) / 70))

        elif property_type == "expression_yield":
            return min(1.0, max(0.0, float(outcome) / 1000))

        elif property_type == "binding_affinity":
            log_outcome = math.log10(float(outcome))
            log_min = math.log10(0.1)
            log_max = math.log10(1000)
            return max(0.0, min(1.0, 1.0 - (log_outcome - log_min) / (log_max - log_min)))

        else:
            return float(outcome)

    def _calculate_confidence(
        self, total_weight: float, num_sequences: int
    ) -> float:
        """Calculate confidence based on evidence quality."""
        return min(1.0, (total_weight / 10.0) * (num_sequences / 20.0))
