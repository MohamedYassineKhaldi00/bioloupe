"""
Pattern Extraction Service for Hypothesis Generation.

Extracts common patterns, methodologies, and success factors
from similar experiments to guide hypothesis generation.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a common pattern found in experiments."""

    description: str
    methods: List[str]
    conditions: List[str]
    success_factors: List[str]
    evidence_count: int
    confidence_score: float = 0.0


class PatternExtractor:
    """
    Extracts patterns from similar experiments to guide hypothesis generation.

    Analyzes:
    - Common methodologies across experiments
    - Shared experimental conditions
    - Success factors and outcomes
    - Design principles that work
    """

    def __init__(self, min_pattern_support: int = 3):
        """
        Initialize pattern extractor.

        Args:
            min_pattern_support: Minimum number of experiments to form a pattern
        """
        self.min_pattern_support = min_pattern_support

    async def extract_patterns(
        self, experiments: List[Dict[str, Any]]
    ) -> List[Pattern]:
        """
        Extract common experimental patterns from similar experiments.

        Args:
            experiments: List of similar experiment dictionaries

        Returns:
            List of identified patterns with evidence
        """
        if not experiments:
            logger.warning("No experiments provided for pattern extraction")
            return []

        logger.info("Extracting patterns", extra={"experiment_count": len(experiments)})

        # Cluster experiments by similarity
        clusters = self.cluster_experiments(experiments)

        patterns = []
        for cluster in clusters:
            if len(cluster) < self.min_pattern_support:
                continue

            # Extract pattern components
            common_methods = self.find_common_methods(cluster)
            common_conditions = self.find_common_conditions(cluster)
            success_factors = self.identify_success_factors(cluster)

            # Calculate confidence based on cluster size and consistency
            confidence = min(len(cluster) / len(experiments), 1.0)

            pattern = Pattern(
                description=f"Pattern from {len(cluster)} similar experiments",
                methods=common_methods,
                conditions=common_conditions,
                success_factors=success_factors,
                evidence_count=len(cluster),
                confidence_score=confidence,
            )
            patterns.append(pattern)

        logger.info("Extracted patterns", extra={"pattern_count": len(patterns)})
        return patterns

    def cluster_experiments(
        self, experiments: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group experiments by similarity.

        Simple clustering based on shared keywords and methods.
        In production, could use more sophisticated clustering.

        Args:
            experiments: List of experiments to cluster

        Returns:
            List of experiment clusters
        """
        if len(experiments) <= self.min_pattern_support:
            # All experiments in one cluster if too few
            return [experiments]

        # Simple keyword-based clustering
        # Extract keywords from each experiment
        experiment_keywords = []
        for exp in experiments:
            keywords = self._extract_keywords(exp)
            experiment_keywords.append(keywords)

        # Calculate similarity matrix
        clusters = []
        used = set()

        for i, keywords_i in enumerate(experiment_keywords):
            if i in used:
                continue

            cluster = [experiments[i]]
            used.add(i)

            for j, keywords_j in enumerate(experiment_keywords):
                if j <= i or j in used:
                    continue

                # Calculate Jaccard similarity
                similarity = self._jaccard_similarity(keywords_i, keywords_j)
                if similarity > 0.3:  # Threshold for grouping
                    cluster.append(experiments[j])
                    used.add(j)

            if len(cluster) >= self.min_pattern_support:
                clusters.append(cluster)

        # Add singleton clusters if needed
        if not clusters and experiments:
            clusters = [experiments]

        return clusters

    def find_common_methods(
        self, experiments: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Find common methodologies across experiments.

        Args:
            experiments: Cluster of similar experiments

        Returns:
            List of common method descriptions
        """
        method_counter = Counter()

        for exp in experiments:
            methods_text = exp.get("methods", "")
            if not methods_text:
                continue

            # Extract method keywords/phrases
            # In production, could use NLP for better extraction
            method_keywords = self._extract_method_keywords(methods_text)
            method_counter.update(method_keywords)

        # Return methods that appear in at least 50% of experiments
        threshold = len(experiments) * 0.5
        common_methods = [
            method for method, count in method_counter.items() if count >= threshold
        ]

        return common_methods[:10]  # Top 10 most common

    def find_common_conditions(
        self, experiments: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Find common experimental conditions.

        Args:
            experiments: Cluster of similar experiments

        Returns:
            List of common condition descriptions
        """
        condition_counter = Counter()

        for exp in experiments:
            # Look for conditions in metadata
            metadata = exp.get("metadata", {})

            # Extract condition-related fields
            conditions = []
            if "temperature" in metadata:
                conditions.append(f"temperature: {metadata['temperature']}")
            if "pH" in metadata:
                conditions.append(f"pH: {metadata['pH']}")
            if "duration" in metadata:
                conditions.append(f"duration: {metadata['duration']}")

            # Also check methods text for conditions
            methods_text = exp.get("methods", "")
            if methods_text:
                condition_keywords = self._extract_condition_keywords(methods_text)
                conditions.extend(condition_keywords)

            condition_counter.update(conditions)

        # Return conditions appearing in at least 40% of experiments
        threshold = len(experiments) * 0.4
        common_conditions = [
            cond for cond, count in condition_counter.items() if count >= threshold
        ]

        return common_conditions[:10]

    def identify_success_factors(
        self, experiments: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Identify factors associated with successful outcomes.

        Args:
            experiments: Cluster of experiments (presumably successful)

        Returns:
            List of success factor descriptions
        """
        success_factors = []

        # Analyze results sections for success indicators
        result_keywords = Counter()

        for exp in experiments:
            results_text = exp.get("results", "")
            if not results_text:
                continue

            # Extract positive outcome keywords
            keywords = self._extract_success_keywords(results_text)
            result_keywords.update(keywords)

        # Most common success indicators
        for keyword, count in result_keywords.most_common(10):
            if count >= len(experiments) * 0.3:
                success_factors.append(keyword)

        # Add generic success factors if none found
        if not success_factors:
            success_factors = [
                "Reproducible methodology",
                "Well-controlled conditions",
                "Appropriate sample size",
            ]

        return success_factors

    def _extract_keywords(self, experiment: Dict[str, Any]) -> set:
        """Extract keywords from experiment for clustering."""
        keywords = set()

        # Extract from title
        title = experiment.get("title", "")
        if title:
            words = title.lower().split()
            keywords.update(w for w in words if len(w) > 3)

        # Extract from abstract
        abstract = experiment.get("abstract", "")
        if abstract:
            words = abstract.lower().split()[:100]  # First 100 words
            keywords.update(w for w in words if len(w) > 4)

        return keywords

    def _extract_method_keywords(self, methods_text: str) -> List[str]:
        """Extract method keywords from methods section."""
        # Common method keywords in biotech
        method_terms = [
            "PCR", "sequencing", "cloning", "transfection", "CRISPR",
            "western blot", "ELISA", "immunostaining", "microscopy",
            "flow cytometry", "chromatography", "spectroscopy",
            "gel electrophoresis", "cell culture", "protein purification",
        ]

        methods_lower = methods_text.lower()
        found_methods = [term for term in method_terms if term.lower() in methods_lower]

        return found_methods

    def _extract_condition_keywords(self, methods_text: str) -> List[str]:
        """Extract experimental condition keywords."""
        conditions = []
        methods_lower = methods_text.lower()

        # Temperature patterns
        if "37°c" in methods_lower or "37 °c" in methods_lower:
            conditions.append("37°C incubation")
        if "4°c" in methods_lower or "4 °c" in methods_lower:
            conditions.append("4°C storage")

        # Time patterns
        if "overnight" in methods_lower:
            conditions.append("overnight incubation")
        if "24 h" in methods_lower or "24h" in methods_lower:
            conditions.append("24h treatment")

        # pH patterns
        if "ph 7" in methods_lower:
            conditions.append("pH 7 buffer")

        return conditions

    def _extract_success_keywords(self, results_text: str) -> List[str]:
        """Extract success indicator keywords from results."""
        success_terms = [
            "significant increase", "significant decrease", "improved",
            "enhanced", "successful", "effective", "demonstrated",
            "confirmed", "validated", "reproducible", "consistent",
        ]

        results_lower = results_text.lower()
        found_terms = [term for term in success_terms if term in results_lower]

        return found_terms

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0
