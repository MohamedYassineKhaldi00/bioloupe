from __future__ import annotations

import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.exceptions import CacheException, RateLimitExceeded
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
    def __init__(
        self,
        redis: Redis | None = None,
        max_attempts: int = 5,
        window_seconds: int = 900,
        key_prefix: str = "rate_limit:"
    ) -> None:
        self._redis = redis
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._key_prefix = key_prefix

    def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        try:
            redis = self._get_redis()
            current, ttl = await redis.eval(RATE_LIMIT_SCRIPT, 1, key, window_seconds)
            current = int(current)
            ttl = int(ttl)
            remaining = max(0, limit - current)
            allowed = current <= limit
            return RateLimitResult(allowed=allowed, current=current, remaining=remaining, reset_in=ttl)
        except Exception as exc:
            logger.error("Rate limit check failed", extra={"error": str(exc)})
            raise CacheException(f"Rate limit check failed: {exc}") from exc

    async def check_rate_limit(self, identifier: str) -> None:
        """Check rate limit for an identifier (e.g., email, IP).
        
        Raises RateLimitExceeded if the limit is exceeded.
        """
        key = f"{self._key_prefix}{identifier}"
        result = await self.check(key, self._max_attempts, self._window_seconds)
        if not result.allowed:
            raise RateLimitExceeded(
                remaining=result.remaining,
                reset_in=result.reset_in
            )
