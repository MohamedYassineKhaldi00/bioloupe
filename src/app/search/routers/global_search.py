from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.common import DBSessionDep
from app.search.models.global_models import AutocompleteResponse, GlobalSearchRequest, GlobalSearchResponse
from app.search.routers.dependencies import (
    get_cache_service,
    get_search_analytics_service,
)
from app.search.services.global_search import GlobalSearchService


router = APIRouter(prefix="/search/global", tags=["search-global"])


def get_global_search_service(
    db: AsyncSession = Depends(DBSessionDep),
    analytics=Depends(get_search_analytics_service),
    cache=Depends(get_cache_service),
) -> GlobalSearchService:
    return GlobalSearchService(db, analytics, cache)


@router.post("", response_model=GlobalSearchResponse)
async def global_search(
    request: GlobalSearchRequest,
    service: GlobalSearchService = Depends(get_global_search_service),
    user=Depends(get_current_active_user),
) -> GlobalSearchResponse:
    return await service.search(request)


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    q: str = Query(..., min_length=1),
    service: GlobalSearchService = Depends(get_global_search_service),
) -> AutocompleteResponse:
    suggestions = await service.autocomplete(q)
    return AutocompleteResponse(suggestions=suggestions)
