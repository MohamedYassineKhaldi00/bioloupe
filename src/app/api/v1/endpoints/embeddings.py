"""Embedding generation endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.common import DBSessionDep
from app.core.exceptions import EmbeddingError
from app.models.material import Material
from app.models.session import SessionPermission
from app.schemas.embedding import (
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    EmbeddingResponse,
)
from app.services.embedding.unified_embedding import UnifiedEmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


def get_unified_service() -> UnifiedEmbeddingService:
    """Get unified embedding service instance."""
    return UnifiedEmbeddingService()


@router.post(
    "/generate/{material_id}",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_embedding(
    material_id: uuid.UUID,
    db: DBSessionDep,
    service: Annotated[UnifiedEmbeddingService, Depends(get_unified_service)],
) -> EmbeddingResponse:
    """Generate embedding for a material.

    Args:
        material_id: Material UUID
        db: Database session
        service: Unified embedding service

    Returns:
        Embedding response with vector

    Raises:
        HTTPException: If material not found or embedding fails
    """
    result = await db.execute(
        select(Material).where(Material.id == material_id)
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    try:
        start_time = time.time()
        embedding = await service.embed_material(material)
        generation_time = (time.time() - start_time) * 1000

        logger.info(
            f"Generated embedding for {material_id} in {generation_time:.2f}ms"
        )

        return EmbeddingResponse(
            material_id=material_id,
            embedding=embedding.tolist(),
            dimension=len(embedding),
            model_name=material.material_type.value,
            cached=False,
        )

    except EmbeddingError as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/batch",
    response_model=BatchEmbeddingResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_batch_embeddings(
    request: BatchEmbeddingRequest,
    db: DBSessionDep,
    service: Annotated[UnifiedEmbeddingService, Depends(get_unified_service)],
) -> BatchEmbeddingResponse:
    """Generate embeddings for batch of materials.

    Args:
        request: Batch embedding request
        db: Database session
        service: Unified embedding service

    Returns:
        Batch embedding response

    Raises:
        HTTPException: If batch processing fails
    """
    result = await db.execute(
        select(Material).where(Material.id.in_(request.material_ids))
    )
    materials = list(result.scalars().all())

    if not materials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No materials found for provided IDs",
        )

    embeddings_dict = await service.embed_batch(materials)

    embeddings_response = {
        str(mat_id): emb.tolist()
        for mat_id, emb in embeddings_dict.items()
    }

    successful = len(embeddings_response)
    failed = len(request.material_ids) - successful

    errors = {}
    for mat_id in request.material_ids:
        if str(mat_id) not in embeddings_response:
            errors[str(mat_id)] = "Failed to generate embedding"

    return BatchEmbeddingResponse(
        embeddings=embeddings_response,
        successful=successful,
        failed=failed,
        errors=errors,
    )


@router.get(
    "/{material_id}",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_cached_embedding(
    material_id: uuid.UUID,
    db: DBSessionDep,
    service: Annotated[UnifiedEmbeddingService, Depends(get_unified_service)],
) -> EmbeddingResponse:
    """Retrieve cached embedding for material.

    Args:
        material_id: Material UUID
        db: Database session
        service: Unified embedding service

    Returns:
        Cached embedding response

    Raises:
        HTTPException: If material not found or no cached embedding
    """
    result = await db.execute(
        select(Material).where(Material.id == material_id)
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    cached_embedding = await service._get_cached_embedding(material_id)

    if cached_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cached embedding found",
        )

    return EmbeddingResponse(
        material_id=material_id,
        embedding=cached_embedding.tolist(),
        dimension=len(cached_embedding),
        model_name=material.material_type.value,
        cached=True,
    )


@router.delete(
    "/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def invalidate_embedding_cache(
    material_id: uuid.UUID,
    service: Annotated[UnifiedEmbeddingService, Depends(get_unified_service)],
) -> None:
    """Invalidate cached embedding.

    Args:
        material_id: Material UUID
        service: Unified embedding service
    """
    await service.invalidate_cache(material_id)
