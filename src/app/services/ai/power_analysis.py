"""Statistical power analysis for experiment design."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class PowerAnalyzer:
    """Calculate statistical power and sample sizes."""

    def calculate_sample_size(
        self,
        effect_size: float,
        alpha: float = 0.05,
        power: float = 0.8,
        test_type: str = "two_sample_t_test",
    ) -> dict[str, Any]:
        """
        Calculate required sample size for desired statistical power.

        Args:
            effect_size: Expected effect size (Cohen's d)
            alpha: Type I error rate (default 0.05)
            power: Desired statistical power (default 0.8)
            test_type: Type of statistical test

        Returns:
            Dictionary with sample size recommendations
        """
        if test_type == "two_sample_t_test":
            n = self._calculate_t_test_sample_size(effect_size, alpha, power)
        else:
            n = self._estimate_sample_size_generic(effect_size, alpha, power)

        return {
            "recommended_sample_size_per_group": int(math.ceil(n)),
            "power": power,
            "alpha": alpha,
            "effect_size": effect_size,
            "test_type": test_type,
            "notes": self._generate_notes(n, power, alpha),
        }

    def _calculate_t_test_sample_size(
        self, effect_size: float, alpha: float, power: float
    ) -> float:
        """Calculate sample size for two-sample t-test."""
        # Simplified formula: n ≈ 2 * (z_α/2 + z_β)² / d²
        # Where d is effect size, z_α/2 and z_β are critical values

        # Approximate z-scores
        z_alpha = 1.96 if alpha == 0.05 else 2.576  # Two-tailed
        z_beta = 0.842 if power == 0.8 else (1.282 if power == 0.9 else 0.524)

        n_per_group = 2 * ((z_alpha + z_beta) ** 2) / (effect_size ** 2)

        return n_per_group

    def _estimate_sample_size_generic(
        self, effect_size: float, alpha: float, power: float
    ) -> float:
        """Generic sample size estimation."""
        # Rule of thumb: n ≈ 16 / d² for power = 0.8, alpha = 0.05
        base_n = 16 / (effect_size ** 2)

        # Adjust for different power/alpha
        if power > 0.8:
            base_n *= 1.5
        if alpha < 0.05:
            base_n *= 1.3

        return base_n

    def _generate_notes(self, n: float, power: float, alpha: float) -> str:
        """Generate interpretive notes for sample size."""
        notes = []

        if n < 10:
            notes.append("Small sample size may limit generalizability")
        elif n > 100:
            notes.append("Large sample size provides robust statistical power")

        if power < 0.8:
            notes.append("Power below 0.8 may miss true effects")
        elif power > 0.9:
            notes.append("High power ensures detection of effects")

        return "; ".join(notes) if notes else "Sample size appropriate"

    def calculate_minimum_detectable_effect(
        self, n_per_group: int, alpha: float = 0.05, power: float = 0.8
    ) -> float:
        """Calculate minimum effect size detectable with given sample."""
        z_alpha = 1.96 if alpha == 0.05 else 2.576
        z_beta = 0.842 if power == 0.8 else (1.282 if power == 0.9 else 0.524)

        effect_size = (z_alpha + z_beta) * math.sqrt(2 / n_per_group)

        return effect_size
