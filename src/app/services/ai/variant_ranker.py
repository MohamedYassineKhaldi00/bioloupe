"""Variant ranking service for sequence optimization."""

from __future__ import annotations

import logging
from typing import Any

from app.services.ai.success_predictor import SuccessPredictor
from app.services.qdrant_service import QdrantService
from app.services.embedding.sequence_embedding import SequenceEmbeddingService

logger = logging.getLogger(__name__)


class VariantRanker:
    """Rank sequence variants by predicted success."""

    def __init__(
        self,
        qdrant_service: QdrantService,
        sequence_embedding_service: SequenceEmbeddingService,
        success_predictor: SuccessPredictor | None = None,
    ):
        self.qdrant = qdrant_service
        self.seq_embed = sequence_embedding_service
        self.predictor = success_predictor or SuccessPredictor()

    async def rank_variants(
        self,
        candidate_sequences: list[dict[str, Any]],
        target_property: str,
        session_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank sequence variants by predicted success."""
        ranked_variants = []

        for sequence in candidate_sequences:
            ranked_variant = await self._rank_single_variant(
                sequence, target_property
            )
            ranked_variants.append(ranked_variant)

        return sorted(
            ranked_variants, key=lambda v: v["success_score"], reverse=True
        )

    async def _rank_single_variant(
        self, sequence: dict[str, Any], target_property: str
    ) -> dict[str, Any]:
        """Rank a single variant."""
        embedding = await self.seq_embed.embed_sequence(
            sequence=sequence["sequence"],
            sequence_type=sequence.get("sequence_type", "protein"),
        )

        similar_sequences = await self._find_similar_with_outcomes(
            query_embedding=embedding, target_property=target_property, limit=100
        )

        success_score, confidence = self.predictor.calculate_success_score(
            similar_sequences, target_property
        )

        evidence = self._compile_evidence(similar_sequences, target_property)

        return {
            "sequence": sequence,
            "success_score": success_score,
            "confidence": confidence,
            "evidence": evidence,
            "recommended_priority": self._get_priority(success_score),
        }

    async def _find_similar_with_outcomes(
        self, query_embedding: list[float], target_property: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Find similar sequences with experimental outcomes."""
        results = await self.qdrant.search_vectors(
            collection="bioloupe_sequences",
            query_vector=query_embedding,
            limit=limit,
            query_filter={
                "must": [
                    {"key": "has_experimental_data", "match": {"value": True}},
                    {"key": "property_measured", "match": {"value": target_property}},
                ]
            },
        )

        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]

    def _compile_evidence(
        self, similar_sequences: list[dict[str, Any]], target_property: str
    ) -> list[dict[str, Any]]:
        """Compile top evidence supporting the ranking."""
        evidence = []

        for seq in similar_sequences[:5]:
            outcome = seq["payload"]["metadata"]["outcomes"].get(target_property)

            item = {
                "sequence_id": seq["payload"].get("uniprot_id") or seq["id"],
                "similarity": seq["score"],
                "outcome_value": outcome,
                "outcome_type": target_property,
                "source": seq["payload"].get("source", "unknown"),
                "description": (
                    f"Similar sequence ({seq['score']:.2%} similarity) "
                    f"achieved {outcome} {target_property}"
                ),
            }
            evidence.append(item)

        return evidence

    def _get_priority(self, success_score: float) -> str:
        """Determine priority level."""
        if success_score > 0.7:
            return "high"
        elif success_score > 0.4:
            return "medium"
        else:
            return "low"

    async def explain_ranking(
        self, variant: dict[str, Any], llm_client: Any
    ) -> str:
        """Generate human-readable explanation for ranking."""
        evidence_text = "\n".join(
            f"- {e['description']}" for e in variant.get("evidence", [])[:3]
        )

        prompt = f"""Explain why this sequence variant is ranked with a success score of {variant['success_score']:.2f} (confidence: {variant['confidence']:.2f}).

Sequence: {variant['sequence']['sequence'][:100]}...

Evidence from similar variants:
{evidence_text}

Provide a concise scientific explanation suitable for researchers."""

        explanation = await llm_client.generate(prompt, max_tokens=300)
        return explanation
