from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Optional
import numpy as np

from app.schemas.search_schemas import SearchRequest, SearchResponse
from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.sessions import require_session_permission
from app.services.similarity_service import SimilarityService
from app.db.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/similar", response_model=SearchResponse)
async def search_similar(
    request: SearchRequest,
    current_user=Depends(get_current_active_user),
    _session=Depends(lambda: require_session_permission("", ["read"])),
    similarity: SimilarityService = Depends(SimilarityService),
) -> SearchResponse:
    query_vector = np.array(request.query_vector)
    results = await similarity.search_similar(
        collection=request.collection,
        query_vector=query_vector,
        filters=request.filters,
        limit=request.limit,
    )

    return SearchResponse(results=results, total=len(results), search_time_ms=0)
