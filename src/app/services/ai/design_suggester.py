"""Experiment design suggestion service."""

from __future__ import annotations

import logging
import json
from typing import Any

from app.services.ai.power_analysis import PowerAnalyzer
from app.services.ai.llm_client import LLMClient
from app.services.ai.evidence_retrieval import EvidenceRetriever

logger = logging.getLogger(__name__)


class DesignSuggester:
    """Generate optimal experiment design recommendations."""

    def __init__(
        self,
        llm_client: LLMClient,
        evidence_retriever: EvidenceRetriever,
        power_analyzer: PowerAnalyzer | None = None,
    ):
        self.llm = llm_client
        self.evidence = evidence_retriever
        self.power_analyzer = power_analyzer or PowerAnalyzer()

    async def suggest_experiment_design(
        self,
        experiment_goal: str,
        hypothesis: str | None,
        available_resources: dict[str, Any],
        constraints: list[str],
        session_id: str,
    ) -> dict[str, Any]:
        """
        Suggest optimal experiment design.

        Returns:
            Comprehensive experiment design with controls,
            sample sizes, protocols, and statistical plan
        """
        # Find similar successful experiments
        similar_experiments = await self._find_similar_experiments(
            goal=experiment_goal, session_id=session_id
        )

        # Extract common design patterns
        design_patterns = self._extract_design_patterns(similar_experiments)

        # Generate design using LLM
        design = await self._generate_design_with_llm(
            goal=experiment_goal,
            hypothesis=hypothesis,
            patterns=design_patterns,
            resources=available_resources,
            constraints=constraints,
        )

        # Add statistical power analysis
        design["power_analysis"] = self._add_power_analysis(design)

        return design

    async def _find_similar_experiments(
        self, goal: str, session_id: str
    ) -> list[dict[str, Any]]:
        """Find similar successful experiments from literature."""
        # Use evidence retrieval to find similar experiments
        evidence = await self.evidence.retrieve_evidence(
            query=goal, session_id=session_id, k=10
        )

        # Filter for experiments with statistical significance
        filtered = [
            e
            for e in evidence
            if e.get("metadata", {}).get("peer_reviewed")
            and e.get("metadata", {}).get("statistical_significance")
        ]

        return filtered

    def _extract_design_patterns(
        self, experiments: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract common design elements from experiments."""
        patterns = {
            "common_controls": [],
            "typical_sample_sizes": [],
            "measurement_methods": [],
            "analysis_approaches": [],
        }

        for exp in experiments:
            metadata = exp.get("metadata", {})
            if "control_groups" in metadata:
                patterns["common_controls"].extend(metadata["control_groups"])
            if "sample_size" in metadata:
                patterns["typical_sample_sizes"].append(metadata["sample_size"])

        return patterns

    async def _generate_design_with_llm(
        self,
        goal: str,
        hypothesis: str | None,
        patterns: dict[str, Any],
        resources: dict[str, Any],
        constraints: list[str],
    ) -> dict[str, Any]:
        """Generate design recommendations using LLM."""
        prompt = self._build_design_prompt(
            goal, hypothesis, patterns, resources, constraints
        )

        response = await self.llm.generate(prompt, max_tokens=2000)

        # Parse structured response
        design = self._parse_design_response(response)

        return design

    def _build_design_prompt(
        self,
        goal: str,
        hypothesis: str | None,
        patterns: dict[str, Any],
        resources: dict[str, Any],
        constraints: list[str],
    ) -> str:
        """Build prompt for LLM design generation."""
        return f"""Design an optimal experiment for the following goal:
{goal}

Hypothesis: {hypothesis or "Not specified"}

Successful designs from literature:
{json.dumps(patterns, indent=2)}

Available resources:
{json.dumps(resources, indent=2)}

Constraints:
{', '.join(constraints)}

Provide a detailed experiment design including:
1. Experimental groups (treatment and control)
2. Sample size recommendations
3. Measurement protocols and timepoints
4. Data collection methods
5. Statistical analysis plan
6. Expected outcomes
7. Potential confounding factors

Format as JSON with keys: experimental_groups, sample_size,
measurement_protocol, data_collection, statistical_plan,
expected_outcomes, confounding_factors"""

    def _parse_design_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response into structured design."""
        try:
            design = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to text parsing
            design = {"description": response, "structured": False}

        return design

    def _add_power_analysis(self, design: dict[str, Any]) -> dict[str, Any]:
        """Add statistical power analysis to design."""
        # Extract expected effect size from design
        effect_size = design.get("expected_effect_size", 0.5)

        # Calculate sample size
        power_analysis = self.power_analyzer.calculate_sample_size(
            effect_size=effect_size, alpha=0.05, power=0.8
        )

        return power_analysis
