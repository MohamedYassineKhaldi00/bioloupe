from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis

from app.core.exceptions import CacheException
from app.db.redis_client import get_redis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis or get_redis()

    async def get(self, key: str) -> Any | None:
        try:
            value = await self._redis.get(key)
            if value is None:
                await self._redis.hincrby("cache:metrics", "miss", 1)
                return None
            await self._redis.hincrby("cache:metrics", "hit", 1)
            return json.loads(value)
        except Exception as exc:
            logger.error("Cache get failed", extra={"error": str(exc)})
            raise CacheException(f"Cache get failed: {exc}") from exc

    async def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            payload = json.dumps(value, default=str)
            await self._redis.set(key, payload, ex=ttl)
        except Exception as exc:
            logger.error("Cache set failed", extra={"error": str(exc)})
            raise CacheException(f"Cache set failed: {exc}") from exc

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception as exc:
            logger.error("Cache delete failed", extra={"error": str(exc)})
            raise CacheException(f"Cache delete failed: {exc}") from exc

    async def invalidate_prefix(self, prefix: str) -> None:
        try:
            async for key in self._redis.scan_iter(match=f"{prefix}*"):
                await self._redis.delete(key)
        except Exception as exc:
            logger.error("Cache invalidation failed", extra={"error": str(exc)})
            raise CacheException(f"Cache invalidation failed: {exc}") from exc

    async def get_or_set(
        self,
        key: str,
        ttl: int,
        loader: Callable[[], Awaitable[Any]],
    ) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await loader()
        await self.set(key, value, ttl)
        return value

    async def warm(self, entries: dict[str, tuple[Any, int]]) -> None:
        try:
            for key, (value, ttl) in entries.items():
                await self.set(key, value, ttl)
        except Exception as exc:
            logger.error("Cache warm failed", extra={"error": str(exc)})
            raise CacheException(f"Cache warm failed: {exc}") from exc
