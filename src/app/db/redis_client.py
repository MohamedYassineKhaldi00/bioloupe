from __future__ import annotations

import logging
from redis.asyncio import ConnectionPool, Redis, RedisCluster
from typing import Dict, Any, Set

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_cluster: RedisCluster | None = None


class MockRedis:
    """Mock Redis for local development without Redis server"""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.sets: Dict[str, Set[str]] = {}
        
    async def setex(self, key: str, time: int, value: str) -> None:
        self.data[key] = value
        
    async def set(self, key: str, value: str) -> None:
        self.data[key] = value
        
    async def get(self, key: str) -> str | None:
        return self.data.get(key)
        
    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted += 1
            if key in self.sets:
                del self.sets[key]
                deleted += 1
        return deleted
        
    async def sadd(self, key: str, *values: str) -> int:
        if key not in self.sets:
            self.sets[key] = set()
        added = 0
        for value in values:
            if value not in self.sets[key]:
                self.sets[key].add(value)
                added += 1
        return added
        
    async def srem(self, key: str, *values: str) -> int:
        if key not in self.sets:
            return 0
        removed = 0
        for value in values:
            if value in self.sets[key]:
                self.sets[key].remove(value)
                removed += 1
        return removed
        
    async def smembers(self, key: str) -> Set[str]:
        return self.sets.get(key, set())
        
    async def scan_iter(self, match: str = None):
        for key in self.data:
            if match is None or key.startswith(match.replace("*", "")):
                yield key


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis() -> Redis | RedisCluster | MockRedis:
    try:
        global _cluster
        settings = get_settings()
        if settings.redis_url.startswith("redis+cluster://"):
            if _cluster is None:
                _cluster = RedisCluster.from_url(
                    settings.redis_url.replace("redis+cluster://", "redis://", 1),
                    decode_responses=True,
                )
            return _cluster
        return Redis(connection_pool=_get_pool())
    except Exception as e:
        logger.warning(f"Redis connection failed, using mock Redis: {e}")
        return MockRedis()


async def close_redis() -> None:
    global _pool
    global _cluster
    if _cluster is not None:
        await _cluster.close()
        _cluster = None
    if _pool is not None:
        await _pool.disconnect(inuse_connections=True)
        _pool = None
        logger.info("Redis connection pool closed")
