"""
Hypothesis Generator Service - Main AI-powered hypothesis generation.

Combines evidence retrieval, pattern extraction, and LLM generation
to create testable scientific hypotheses based on session materials.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.schemas.hypothesis_schemas import HypothesisResponse
from app.services.ai.evidence_retrieval import EvidenceRetriever
from app.services.ai.llm_client import LLMClient
from app.services.ai.pattern_extraction import Pattern, PatternExtractor

logger = logging.getLogger(__name__)


class HypothesisGenerator:
    """
    AI-powered scientific hypothesis generator.

    Generates novel, testable hypotheses by:
    1. Analyzing session materials
    2. Finding similar successful experiments
    3. Extracting patterns and methodologies
    4. Using LLM to synthesize creative hypotheses
    5. Ranking by feasibility, evidence, and novelty
    """

    def __init__(
        self,
        llm_client: LLMClient,
        evidence_retriever: EvidenceRetriever,
        pattern_extractor: PatternExtractor,
    ):
        self.llm = llm_client
        self.evidence = evidence_retriever
        self.patterns = pattern_extractor

    async def generate_hypotheses(
        self,
        session_id: UUID,
        research_goal: str,
        num_hypotheses: int = 5,
        focus_area: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> List[HypothesisResponse]:
        """
        Generate scientific hypotheses for a research session.

        Process:
        1. Get session materials and context
        2. Find similar successful experiments from literature
        3. Extract common patterns and approaches
        4. Use LLM to generate novel hypotheses
        5. Rank by feasibility, evidence support, and novelty

        Args:
            session_id: Research session to analyze
            research_goal: Research goal or question
            num_hypotheses: Number of hypotheses to generate (1-20)
            focus_area: Optional specific focus area
            llm_model: Optional LLM model override

        Returns:
            List of ranked hypothesis responses
        """
        logger.info(
            "Starting hypothesis generation",
            extra={
                "session_id": str(session_id),
                "research_goal": research_goal[:100],
                "num_hypotheses": num_hypotheses,
                "focus_area": focus_area,
                "llm_model": llm_model,
            },
        )

        # Step 1: Get session context
        session_context = await self.evidence.get_session_context(session_id)

        # Step 2: Find similar successful experiments
        similar_experiments = await self.evidence.find_similar_experiments(
            session_id=session_id,
            filter_criteria={"outcome": "successful", "peer_reviewed": True},
            limit=50,
        )

        if not similar_experiments:
            logger.warning(
                "No similar experiments found, generating hypotheses without evidence",
                extra={"session_id": str(session_id)},
            )

        # Step 3: Extract patterns
        patterns = await self.patterns.extract_patterns(similar_experiments)

        # Step 4: Generate hypotheses using LLM
        hypotheses = await self._llm_generate_hypotheses(
            research_goal=research_goal,
            session_context=session_context,
            patterns=patterns,
            similar_experiments=similar_experiments,
            num_hypotheses=num_hypotheses,
            focus_area=focus_area,
            llm_model=llm_model,
        )

        # Step 5: Rank hypotheses
        ranked_hypotheses = await self._rank_hypotheses(
            hypotheses=hypotheses,
            evidence=similar_experiments,
        )

        logger.info(
            "Hypothesis generation complete",
            extra={
                "session_id": str(session_id),
                "hypotheses_generated": len(ranked_hypotheses),
                "patterns_used": len(patterns),
                "evidence_count": len(similar_experiments),
            },
        )

        return ranked_hypotheses[:num_hypotheses]

    async def _llm_generate_hypotheses(
        self,
        research_goal: str,
        session_context: Dict[str, Any],
        patterns: List[Pattern],
        similar_experiments: List[Dict[str, Any]],
        num_hypotheses: int,
        focus_area: Optional[str],
        llm_model: Optional[str],
    ) -> List[HypothesisResponse]:
        """Use LLM to generate creative, evidence-backed hypotheses."""

        # Prepare context for LLM
        prompt = self._build_hypothesis_prompt(
            research_goal=research_goal,
            session_context=session_context,
            patterns=patterns,
            experiments=similar_experiments,
            num_hypotheses=num_hypotheses,
            focus_area=focus_area,
        )

        # Call LLM with structured output request
        try:
            response_text = await self.llm.generate(
                prompt=prompt,
                model=llm_model,
                temperature=0.7,
                max_tokens=4000,
            )

            # Parse LLM response into structured hypotheses
            hypotheses = self._parse_llm_response(response_text)

            logger.info(
                "LLM generated hypotheses",
                extra={"count": len(hypotheses), "model": llm_model or "default"},
            )

            return hypotheses

        except Exception as exc:
            logger.error(
                "LLM hypothesis generation failed",
                extra={"error": str(exc)},
                exc_info=True,
            )
            # Return empty list on failure
            return []

    def _build_hypothesis_prompt(
        self,
        research_goal: str,
        session_context: Dict[str, Any],
        patterns: List[Pattern],
        experiments: List[Dict[str, Any]],
        num_hypotheses: int,
        focus_area: Optional[str],
    ) -> str:
        """Build comprehensive prompt for LLM hypothesis generation."""

        materials_summary = self._format_materials(session_context.get("materials", []))
        patterns_summary = self._format_patterns(patterns)
        experiments_summary = self._format_experiments(experiments[:10])  # Top 10

        prompt = f"""You are a scientific research assistant helping biotechnology researchers generate novel, testable hypotheses.

Research Goal: {research_goal}
{f"Focus Area: {focus_area}" if focus_area else ""}

Available Resources in Session:
{materials_summary}

Successful Patterns from Literature:
{patterns_summary}

Similar Successful Experiments:
{experiments_summary}

Task: Generate {num_hypotheses} novel, testable scientific hypotheses that:
1. Build on the successful patterns identified
2. Are feasible given the available resources
3. Address the research goal directly
4. Are specific and measurable
5. Include clear experimental predictions

For each hypothesis, provide in JSON format:
{{
  "hypothesis": "Clear, specific hypothesis statement",
  "rationale": "Scientific rationale explaining why this is likely to work, citing evidence",
  "experimental_approach": "Step-by-step experimental approach to test this hypothesis",
  "expected_outcomes": "Specific, measurable predicted outcomes",
  "required_resources": ["List", "of", "required", "resources"],
  "evidence_citations": ["Supporting paper 1", "Supporting paper 2"]
}}

Generate exactly {num_hypotheses} hypotheses in a JSON array format.
Output only valid JSON, no additional text.
"""

        return prompt

    def _format_materials(self, materials: List[Dict[str, Any]]) -> str:
        """Format session materials for LLM prompt."""
        if not materials:
            return "No materials available in session."

        formatted = []
        for mat in materials[:20]:  # Limit to 20 materials
            mat_type = mat.get("type", "unknown")
            title = mat.get("title", "Untitled")
            formatted.append(f"- {mat_type}: {title}")

        if len(materials) > 20:
            formatted.append(f"- ... and {len(materials) - 20} more materials")

        return "\n".join(formatted)

    def _format_patterns(self, patterns: List[Pattern]) -> str:
        """Format extracted patterns for LLM prompt."""
        if not patterns:
            return "No clear patterns identified from literature."

        formatted = []
        for i, pattern in enumerate(patterns[:5], 1):  # Top 5 patterns
            formatted.append(f"\nPattern {i}: {pattern.description}")
            if pattern.methods:
                formatted.append(f"  Common methods: {', '.join(pattern.methods[:5])}")
            if pattern.success_factors:
                formatted.append(f"  Success factors: {', '.join(pattern.success_factors[:5])}")
            formatted.append(f"  Evidence: {pattern.evidence_count} experiments (confidence: {pattern.confidence_score:.2f})")

        return "\n".join(formatted)

    def _format_experiments(self, experiments: List[Dict[str, Any]]) -> str:
        """Format similar experiments for LLM prompt."""
        if not experiments:
            return "No similar experiments found in literature."

        formatted = []
        for i, exp in enumerate(experiments[:10], 1):  # Top 10
            title = exp.get("title", "No title")
            score = exp.get("score", 0.0)
            formatted.append(f"\n{i}. {title} (similarity: {score:.2f})")

            abstract = exp.get("abstract", "")
            if abstract:
                # Truncate abstract
                abstract_short = abstract[:200] + "..." if len(abstract) > 200 else abstract
                formatted.append(f"   Abstract: {abstract_short}")

        return "\n".join(formatted)

    def _parse_llm_response(self, response_text: str) -> List[HypothesisResponse]:
        """Parse LLM JSON response into hypothesis objects."""
        hypotheses = []

        try:
            # Extract JSON array from response
            # LLM might wrap JSON in markdown code blocks
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = response_text

            # Parse JSON
            hypotheses_data = json.loads(json_text)

            if not isinstance(hypotheses_data, list):
                logger.warning("LLM response is not a JSON array")
                return []

            # Convert to HypothesisResponse objects
            for hyp_data in hypotheses_data:
                try:
                    hypothesis = HypothesisResponse(
                        hypothesis=hyp_data.get("hypothesis", ""),
                        rationale=hyp_data.get("rationale", ""),
                        experimental_approach=hyp_data.get("experimental_approach", ""),
                        expected_outcomes=hyp_data.get("expected_outcomes", ""),
                        required_resources=hyp_data.get("required_resources", []),
                        evidence_citations=hyp_data.get("evidence_citations", []),
                        # Initialize scores (will be calculated in ranking)
                        feasibility_score=0.5,
                        evidence_score=0.5,
                        novelty_score=0.5,
                        overall_score=0.5,
                    )
                    hypotheses.append(hypothesis)
                except Exception as exc:
                    logger.warning(
                        "Failed to parse individual hypothesis",
                        extra={"error": str(exc), "data": hyp_data},
                    )
                    continue

        except json.JSONDecodeError as exc:
            logger.error(
                "Failed to parse LLM JSON response",
                extra={"error": str(exc), "response": response_text[:500]},
            )
        except Exception as exc:
            logger.error(
                "Unexpected error parsing LLM response",
                extra={"error": str(exc)},
                exc_info=True,
            )

        return hypotheses

    async def _rank_hypotheses(
        self,
        hypotheses: List[HypothesisResponse],
        evidence: List[Dict[str, Any]],
    ) -> List[HypothesisResponse]:
        """
        Rank hypotheses by:
        - Feasibility (0-1): How achievable given resources
        - Evidence support (0-1): Strength of supporting literature
        - Novelty (0-1): How novel compared to existing work
        - Overall score: Weighted combination
        """
        for hypothesis in hypotheses:
            # Calculate feasibility score
            hypothesis.feasibility_score = self._calculate_feasibility(hypothesis)

            # Calculate evidence support score
            hypothesis.evidence_score = self._calculate_evidence_support(
                hypothesis, evidence
            )

            # Calculate novelty score
            hypothesis.novelty_score = self._calculate_novelty(hypothesis, evidence)

            # Overall score (weighted average)
            hypothesis.overall_score = (
                0.4 * hypothesis.feasibility_score +
                0.3 * hypothesis.evidence_score +
                0.3 * hypothesis.novelty_score
            )

        # Sort by overall score (descending)
        return sorted(hypotheses, key=lambda h: h.overall_score, reverse=True)

    def _calculate_feasibility(self, hypothesis: HypothesisResponse) -> float:
        """Calculate feasibility score based on hypothesis characteristics."""
        score = 0.5  # Base score

        # More specific approach = more feasible
        if len(hypothesis.experimental_approach) > 100:
            score += 0.2

        # Having specific resources = more feasible
        if len(hypothesis.required_resources) > 0:
            score += 0.1
        if len(hypothesis.required_resources) > 3:
            score += 0.1

        # Not too many resources = more feasible
        if len(hypothesis.required_resources) < 10:
            score += 0.1

        return min(score, 1.0)

    def _calculate_evidence_support(
        self, hypothesis: HypothesisResponse, evidence: List[Dict[str, Any]]
    ) -> float:
        """Calculate evidence support score."""
        score = 0.3  # Base score

        # Having citations = better support
        if len(hypothesis.evidence_citations) > 0:
            score += 0.2
        if len(hypothesis.evidence_citations) > 2:
            score += 0.2

        # Strong rationale = better support
        if len(hypothesis.rationale) > 100:
            score += 0.2

        # More similar experiments = better support
        if len(evidence) > 20:
            score += 0.1

        return min(score, 1.0)

    def _calculate_novelty(
        self, hypothesis: HypothesisResponse, evidence: List[Dict[str, Any]]
    ) -> float:
        """Calculate novelty score (inverse similarity to existing work)."""
        # Simple heuristic: shorter rationale might indicate more novel approach
        # In production, could use semantic similarity to existing work

        score = 0.5  # Base score

        # Longer hypothesis statement = more specific/novel
        if len(hypothesis.hypothesis) > 100:
            score += 0.2

        # Novel approaches mentioned in rationale
        novel_keywords = ["novel", "new", "innovative", "unprecedented", "first"]
        rationale_lower = hypothesis.rationale.lower()
        for keyword in novel_keywords:
            if keyword in rationale_lower:
                score += 0.1
                break

        # If fewer similar experiments, might be more novel area
        if len(evidence) < 10:
            score += 0.2

        return min(score, 1.0)
