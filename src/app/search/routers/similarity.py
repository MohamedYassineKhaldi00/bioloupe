from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_active_user
from app.search.models.similarity_models import SimilarityExplorationRequest, SimilarityExplorationResponse
from app.search.routers.dependencies import get_cache_service, get_qdrant_service
from app.search.services.similarity_explorer import SimilarityExplorationService


router = APIRouter(prefix="/search/similarity", tags=["search-similarity"])


def get_similarity_explorer(
    cache=Depends(get_cache_service),
    vector=Depends(get_qdrant_service),
) -> SimilarityExplorationService:
    return SimilarityExplorationService(vector, cache)


@router.post("", response_model=SimilarityExplorationResponse)
async def similarity_explore(
    request: SimilarityExplorationRequest,
    service: SimilarityExplorationService = Depends(get_similarity_explorer),
    user=Depends(get_current_active_user),
) -> SimilarityExplorationResponse:
    return await service.explore(request)
