from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_active_user
from app.search.models.publication_models import (
    PublicationSearchRequest,
    PublicationSearchResponse,
    SavePublicationSearchRequest,
    SavedPublicationSearchListResponse,
    SavedPublicationSearchResponse,
)
from app.search.routers.dependencies import (
    get_cache_service,
    get_external_publication_client,
    get_qdrant_service,
    get_search_analytics_service,
    get_saved_search_service,
)
from app.search.services.publication_search import PublicationSearchService


router = APIRouter(prefix="/search/publications", tags=["search-publications"])


def get_publication_search_service(
    cache=Depends(get_cache_service),
    vector=Depends(get_qdrant_service),
    external=Depends(get_external_publication_client),
    analytics=Depends(get_search_analytics_service),
    saved_search=Depends(get_saved_search_service),
) -> PublicationSearchService:
    return PublicationSearchService(cache, vector, external, analytics, saved_search)


@router.post("", response_model=PublicationSearchResponse)
async def publication_search(
    request: PublicationSearchRequest,
    service: PublicationSearchService = Depends(get_publication_search_service),
    user=Depends(get_current_active_user),
) -> PublicationSearchResponse:
    return await service.search(request)


@router.post("/saved", response_model=SavedPublicationSearchResponse)
async def save_publication_search(
    request: SavePublicationSearchRequest,
    service: PublicationSearchService = Depends(get_publication_search_service),
    user=Depends(get_current_active_user),
) -> SavedPublicationSearchResponse:
    return await service.save(str(user.id), request)


@router.get("/saved", response_model=SavedPublicationSearchListResponse)
async def list_saved_searches(
    service: PublicationSearchService = Depends(get_publication_search_service),
    user=Depends(get_current_active_user),
) -> SavedPublicationSearchListResponse:
    return await service.list_saved(str(user.id))


@router.delete("/saved/{search_id}", status_code=200)
async def delete_saved_search(
    search_id: str,
    service: PublicationSearchService = Depends(get_publication_search_service),
    user=Depends(get_current_active_user),
) -> dict[str, str]:
    await service.delete_saved(str(user.id), search_id)
    return {"status": "deleted"}
