"""
API endpoints for AI-powered hypothesis generation.
"""

from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.sessions import require_session_permission
from app.db.base import get_db
from app.models import SessionPermission, User
from app.schemas.hypothesis_schemas import (
    HypothesisGenerationRequest,
    HypothesisResponse,
    HypothesesListResponse,
)
from app.services.ai.evidence_retrieval import EvidenceRetriever
from app.services.ai.hypothesis_generator import HypothesisGenerator
from app.services.ai.llm_client import LLMClient
from app.services.ai.pattern_extraction import PatternExtractor
from app.services.material_service import MaterialService
from app.services.qdrant_service import QdrantService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hypotheses", tags=["hypotheses"])


def get_hypothesis_generator(
    db: AsyncSession = Depends(get_db),
) -> HypothesisGenerator:
    """Dependency for hypothesis generator service."""
    # Initialize services
    qdrant_service = QdrantService()
    session_service = SessionService(db)
    material_service = MaterialService(db)

    # Initialize AI services
    llm_client = LLMClient()
    evidence_retriever = EvidenceRetriever(
        qdrant_service=qdrant_service,
        session_service=session_service,
        material_service=material_service,
    )
    pattern_extractor = PatternExtractor()

    # Initialize hypothesis generator
    generator = HypothesisGenerator(
        llm_client=llm_client,
        evidence_retriever=evidence_retriever,
        pattern_extractor=pattern_extractor,
    )

    return generator


@router.post("/generate", response_model=HypothesesListResponse)
async def generate_hypotheses(
    request: HypothesisGenerationRequest,
    generator: HypothesisGenerator = Depends(get_hypothesis_generator),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> HypothesesListResponse:
    """
    Generate AI-powered scientific hypotheses for a research session.

    Analyzes session materials, finds similar successful experiments from literature,
    extracts patterns, and uses LLM to generate novel, testable hypotheses.

    **Required permissions**: Read access to the session

    **Process**:
    1. Analyze session materials and embeddings
    2. Find similar successful experiments from vector database
    3. Extract common methodologies and patterns
    4. Generate hypotheses using LLM (supports any LiteLLM model)
    5. Rank by feasibility, evidence support, and novelty

    **Supported LLM models** (via `llm_model` field):
    - `gpt-4o` - OpenAI GPT-4 Optimized
    - `gpt-4o-mini` - OpenAI GPT-4 Mini (default, faster/cheaper)
    - `claude-3-5-sonnet` - Anthropic Claude 3.5 Sonnet
    - `mistral-large` - Mistral Large
    - `groq/llama-3.1-70b` - Groq Llama 3.1 70B (very fast)
    - Any other LiteLLM-supported model

    **Example request**:
    ```json
    {
      "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "research_goal": "Improve protein-ligand binding affinity for drug discovery",
      "num_hypotheses": 5,
      "focus_area": "directed evolution",
      "llm_model": "gpt-4o-mini"
    }
    ```
    """
    try:
        session_id = UUID(request.session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format",
        ) from exc

    # Check session read permission
    await require_session_permission(
        session_id=session_id,
        required_permission=SessionPermission.read,
        user=current_user,
        db=db,
    )

    logger.info(
        "Hypothesis generation requested",
        extra={
            "session_id": str(session_id),
            "user_id": str(current_user.id),
            "research_goal": request.research_goal[:100],
            "num_hypotheses": request.num_hypotheses,
            "llm_model": request.llm_model,
        },
    )

    try:
        # Generate hypotheses
        hypotheses = await generator.generate_hypotheses(
            session_id=session_id,
            research_goal=request.research_goal,
            num_hypotheses=request.num_hypotheses,
            focus_area=request.focus_area,
            llm_model=request.llm_model,
        )

        # Get metadata for response
        session_service = SessionService(db)
        session = await session_service.get_session_by_id(session_id)

        # Count evidence and patterns used
        # In production, these would be returned from generator
        evidence_count = 0  # Placeholder
        patterns_count = 0  # Placeholder

        response = HypothesesListResponse(
            session_id=str(session_id),
            research_goal=request.research_goal,
            hypotheses=hypotheses,
            model_used=request.llm_model or "gpt-4o-mini",
            evidence_count=evidence_count,
            patterns_identified=patterns_count,
        )

        logger.info(
            "Hypothesis generation completed",
            extra={
                "session_id": str(session_id),
                "hypotheses_count": len(hypotheses),
                "model_used": request.llm_model or "gpt-4o-mini",
            },
        )

        return response

    except Exception as exc:
        logger.error(
            "Hypothesis generation failed",
            extra={
                "session_id": str(session_id),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hypothesis generation failed: {str(exc)}",
        ) from exc


@router.get("/models", response_model=List[str])
async def list_supported_models(
    current_user: User = Depends(get_current_active_user),
) -> List[str]:
    """
    List supported LLM models for hypothesis generation.

    Returns common LiteLLM model names. Any LiteLLM-supported model can be used.

    **Note**: Actual availability depends on API keys configured in environment.
    """
    # Common models across major providers
    models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "claude-3-5-sonnet",
        "claude-3-5-haiku",
        "claude-3-opus",
        "mistral-large",
        "mistral-medium",
        "groq/llama-3.1-70b",
        "groq/llama-3.1-8b",
        "groq/mixtral-8x7b",
    ]

    return models
