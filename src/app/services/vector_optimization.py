from __future__ import annotations

from typing import Iterable

from qdrant_client.http import models as rest

from app.core.config import Settings, get_settings
from app.services.performance_cache import PerformanceCacheService
from app.services.qdrant_service import QdrantService


class VectorOptimizationService:
    def __init__(
        self,
        qdrant: QdrantService,
        cache: PerformanceCacheService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._qdrant = qdrant
        self._cache = cache or PerformanceCacheService()
        self._settings = settings or get_settings()

    async def search_with_cache(
        self,
        collection: str,
        query_vector: Iterable[float],
        limit: int = 10,
        quantization_config: rest.QuantizationConfig | None = None,
    ) -> tuple[list[dict], bool]:
        cached = await self._cache.get_vector_search(collection, query_vector)
        if cached is not None:
            return cached, True

        points = await self._qdrant.search_vectors(collection, list(query_vector), limit=limit)
        formatted = [self._format_point(point) for point in points]
        await self._cache.cache_vector_search(
            collection,
            query_vector,
            formatted,
            ttl=self._settings.vector_search_cache_ttl_seconds,
        )
        return formatted, False

    async def tune_quantization(
        self,
        collection: str,
        quantization: rest.QuantizationConfig | None = None,
        hnsw_config: rest.HnswConfigDiff | None = None,
    ) -> None:
        if quantization is None and hnsw_config is None:
            return
        await self._qdrant.update_collection_config(collection, quantization, hnsw_config)

    async def monitor_collection(self, collection: str) -> dict[str, object]:
        info = await self._qdrant.collection_info(collection)
        stats = await self._qdrant.collection_stats(collection)
        return {
            "collection": collection,
            "vectors_count": stats.vectors_count,
            "config": info.config.json() if hasattr(info, "config") else None,
            "storage_size": stats.optimizers_config if hasattr(stats, "optimizers_config") else None,
        }

    def _format_point(self, point: rest.ScoredPoint) -> dict[str, object]:
        payload = point.payload or {}
        return {
            "id": str(point.id),
            "score": float(point.score) if point.score is not None else 0.0,
            "payload": payload,
        }
