"""API endpoints for variant ranking."""

from __future__ import annotations

import logging
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.sessions import require_session_permission
from app.db.base import get_db
from app.models import User
from app.schemas.variant_schemas import (
    VariantRankingRequest,
    VariantRankingResponse,
    RankedVariant,
)
from app.services.ai.variant_ranker import VariantRanker
from app.services.ai.success_predictor import SuccessPredictor
from app.services.qdrant_service import QdrantService
from app.services.embedding.sequence_embedding import SequenceEmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/variants", tags=["variants"])


def get_variant_ranker(db: AsyncSession = Depends(get_db)) -> VariantRanker:
    """Dependency for variant ranker service."""
    qdrant_service = QdrantService()
    seq_embedding = SequenceEmbeddingService()
    success_predictor = SuccessPredictor()

    return VariantRanker(
        qdrant_service=qdrant_service,
        sequence_embedding_service=seq_embedding,
        success_predictor=success_predictor,
    )


@router.post("/sessions/{session_id}/rank", response_model=VariantRankingResponse)
async def rank_sequence_variants(
    session_id: str,
    request: VariantRankingRequest,
    ranker: VariantRanker = Depends(get_variant_ranker),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> VariantRankingResponse:
    """
    Rank sequence variants by predicted success.

    Analyzes candidate sequences and predicts success probability
    based on similar sequences with known experimental outcomes.
    """
    # Verify session access
    await require_session_permission(["write", "admin"])

    # Rank variants
    ranked_variants = await ranker.rank_variants(
        candidate_sequences=request.sequences,
        target_property=request.target_property,
    )

    # Store ranking results
    ranking_id = str(uuid4())

    # Calculate summary statistics
    high_priority = sum(1 for v in ranked_variants if v["success_score"] > 0.7)
    medium_priority = sum(
        1 for v in ranked_variants if 0.4 <= v["success_score"] <= 0.7
    )
    low_priority = sum(1 for v in ranked_variants if v["success_score"] < 0.4)

    # Convert to response models
    ranked_variant_models = [RankedVariant(**v) for v in ranked_variants]
    recommended = ranked_variant_models[: request.max_variants_to_test]

    return VariantRankingResponse(
        ranking_id=ranking_id,
        ranked_variants=ranked_variant_models,
        recommended_for_testing=recommended,
        summary={
            "total_variants": len(ranked_variants),
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
        },
    )


@router.post("/rankings/{ranking_id}/explain/{variant_id}")
async def explain_variant_ranking(
    ranking_id: str,
    variant_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Generate detailed explanation for a variant's ranking."""
    # This would fetch from stored rankings
    # For now, return placeholder
    return {
        "variant_id": variant_id,
        "explanation": "Explanation generation requires stored ranking data",
    }
