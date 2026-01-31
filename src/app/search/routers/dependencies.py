from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.common import DBSessionDep
from app.search.db.saved_search_repository import SavedSearchRepository
from app.search.services.external_publications import ExternalPublicationClient
from app.search.services.search_analytics import SearchAnalyticsService
from app.search.services.saved_search_service import SavedSearchService
from app.services.cache_service import CacheService
from app.services.qdrant_service import QdrantService


def get_cache_service() -> CacheService:
    return CacheService()


def get_search_analytics_service() -> SearchAnalyticsService:
    return SearchAnalyticsService()


def get_qdrant_service() -> QdrantService:
    return QdrantService()


def get_external_publication_client() -> ExternalPublicationClient:
    return ExternalPublicationClient()


def get_saved_search_service(db: AsyncSession = Depends(DBSessionDep)) -> SavedSearchService:
    return SavedSearchService(SavedSearchRepository(db))
