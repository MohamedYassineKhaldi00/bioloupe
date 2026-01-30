from __future__ import annotations

import hashlib
import logging
from typing import Iterable

from app.core.config import get_settings
from app.search.models.publication_models import (
    PublicationQuerySource,
    PublicationSearchRequest,
    PublicationSearchResponse,
    PublicationSearchResult,
    SavedPublicationSearchResponse,
    SavedPublicationSearchListResponse,
    SavePublicationSearchRequest,
)
from app.search.services.external_publications import ExternalPublicationClient
from app.search.services.search_analytics import SearchAnalyticsService
from app.search.services.saved_search_service import SavedSearchService
from app.services.cache_service import CacheService
from app.services.qdrant_service import QdrantService
from qdrant_client.http import models as rest

logger = logging.getLogger(__name__)


class PublicationSearchService:
    def __init__(
        self,
        cache: CacheService,
        vector_service: QdrantService,
        external_client: ExternalPublicationClient,
        analytics: SearchAnalyticsService,
        saved_search: SavedSearchService,
    ) -> None:
        self._cache = cache
        self._vector_service = vector_service
        self._external = external_client
        self._analytics = analytics
        self._saved_search = saved_search
        self._settings = get_settings()

    async def search(self, request: PublicationSearchRequest) -> PublicationSearchResponse:
        await self._analytics.record_query(request.query, [source.value for source in request.sources])
        results = []
        for source in request.sources:
            key = f"search:publication:{source.value}:{request.query.lower()}:{request.page}:{request.limit}"
            cached = await self._cache.get(key)
            if cached:
                results.extend([PublicationSearchResult(**item) for item in cached])
                continue

            raw = await self._fetch_source(source, request)
            enriched = await self._enrich_raw(raw, request)
            await self._cache.set(key, [item.model_dump() for item in enriched], ttl=self._settings.publication_cache_ttl_seconds)
            results.extend(enriched)

        return PublicationSearchResponse(query=request.query, total=len(results), results=results)

    async def save(self, user_id: str, request: SavePublicationSearchRequest) -> SavedPublicationSearchResponse:
        saved = await self._saved_search.save(user_id, request)
        return SavedPublicationSearchResponse(**saved)

    async def list_saved(self, user_id: str) -> SavedPublicationSearchListResponse:
        saved = await self._saved_search.list_for_user(user_id)
        return SavedPublicationSearchListResponse(saved_searches=[SavedPublicationSearchResponse(**entry) for entry in saved])

    async def delete_saved(self, user_id: str, search_id: str) -> None:
        await self._saved_search.delete(user_id, search_id)

    async def _fetch_source(self, source: PublicationQuerySource, request: PublicationSearchRequest) -> list[dict]:
        if source == PublicationQuerySource.pubmed:
            records = await self._external.search_pubmed(request.query, request.page, request.limit)
        else:
            records = await self._external.search_arxiv(request.query, request.page, request.limit)
        for record in records:
            record.setdefault("source", source.value)
        return records

    async def _enrich_raw(self, raw: list[dict], request: PublicationSearchRequest) -> list[PublicationSearchResult]:
        vector = self._vector_for_query(request.query)
        try:
            similar = await self._vector_service.search_vectors("materials", vector, limit=3)
        except Exception as exc:
            logger.warning("Unable to enrich publications with Qdrant", extra={"error": str(exc)})
            similar = []

        material_lookup = [self._build_material_summary(point) for point in similar]
        enriched = []
        for record in raw:
            value = record.get("source", PublicationQuerySource.pubmed.value)
            try:
                source_enum = PublicationQuerySource(value)
            except ValueError:
                source_enum = PublicationQuerySource.pubmed
            enriched.append(
                PublicationSearchResult(
                    title=record.get("title", ""),
                    snippet=record.get("snippet"),
                    source=source_enum,
                    publication_id=record.get("publication_id", ""),
                    score=record.get("score", 0.0) or 0.5,
                    metadata=record.get("metadata", {}),
                    similar_materials=material_lookup,
                )
            )
        return enriched

    def _vector_for_query(self, query: str) -> list[float]:
        digest = hashlib.sha256(query.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[:32]]

    def _build_material_summary(self, point: rest.ScoredPoint) -> dict[str, object]:
        payload = point.payload or {}
        return {
            "material_id": payload.get("material_id"),
            "title": payload.get("title"),
            "score": float(point.score) if point.score is not None else 0.0,
            "metadata": payload,
        }
