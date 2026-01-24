from __future__ import annotations

import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.exceptions import CacheException
from app.db.redis_client import get_redis

logger = logging.getLogger(__name__)

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    current: int
    remaining: int
    reset_in: int


class RateLimiter:
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis or get_redis()

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        try:
            current, ttl = await self._redis.eval(RATE_LIMIT_SCRIPT, 1, key, window_seconds)
            current = int(current)
            ttl = int(ttl)
            remaining = max(0, limit - current)
            allowed = current <= limit
            return RateLimitResult(allowed=allowed, current=current, remaining=remaining, reset_in=ttl)
        except Exception as exc:
            logger.error("Rate limit check failed", extra={"error": str(exc)})
            raise CacheException(f"Rate limit check failed: {exc}") from exc
