from __future__ import annotations

import logging
from redis.asyncio import ConnectionPool, Redis, RedisCluster

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_cluster: RedisCluster | None = None


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


def get_redis() -> Redis | RedisCluster:
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
