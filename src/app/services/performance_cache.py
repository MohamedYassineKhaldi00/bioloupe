from __future__ import annotations

import hashlib
from typing import Any, Iterable

from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.db.redis_client import get_redis
from app.services.cache_service import CacheService


class PerformanceCacheService:
    def __init__(
        self,
        cache: CacheService | None = None,
        redis_client: Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._cache = cache or CacheService()
        self._redis = redis_client or get_redis()
        self._settings = settings or get_settings()

    def _vector_key(self, collection: str, vector: Iterable[float]) -> str:
        digest = hashlib.sha256(
            f"{collection}:{','.join(str(v) for v in vector)}".encode("utf-8")
        ).hexdigest()
        return f"vector:search:{collection}:{digest}"

    def _embedding_key(self, identifier: str, version: int) -> str:
        return f"embedding:{identifier}:v{version}"

    async def cache_vector_search(
        self,
        collection: str,
        query_vector: Iterable[float],
        results: Any,
        ttl: int | None = None,
    ) -> str:
        key = self._vector_key(collection, query_vector)
        await self._cache.set(key, results, ttl or self._settings.vector_search_cache_ttl_seconds)
        return key

    async def get_vector_search(self, collection: str, query_vector: Iterable[float]) -> Any | None:
        key = self._vector_key(collection, query_vector)
        return await self._cache.get(key)

    async def invalidate_vector_cache(self, collection: str, query_vector: Iterable[float] | None = None) -> None:
        if query_vector is None:
            await self._cache.invalidate_prefix(f"vector:search:{collection}")
            return
        key = self._vector_key(collection, query_vector)
        await self._cache.delete(key)

    async def cache_embedding_vector(
        self,
        identifier: str,
        vector: Iterable[float],
        version: int,
        ttl: int | None = None,
    ) -> str:
        key = self._embedding_key(identifier, version)
        payload = {"vector": list(vector), "version": version}
        await self._cache.set(key, payload, ttl or self._settings.embedding_cache_ttl_seconds)
        return key

    async def get_cached_embedding(self, identifier: str, version: int) -> Any | None:
        key = self._embedding_key(identifier, version)
        return await self._cache.get(key)

    async def invalidate_embedding_cache(self, identifier: str) -> None:
        prefix = f"embedding:{identifier}"
        await self._cache.invalidate_prefix(prefix)

    async def cache_response(self, key: str, payload: Any, ttl: int) -> None:
        await self._cache.set(key, payload, ttl)

    async def get_cached_response(self, key: str) -> Any | None:
        return await self._cache.get(key)

    async def get_cache_metrics(self) -> dict[str, str]:
        return await self._redis.hgetall("cache:metrics")
