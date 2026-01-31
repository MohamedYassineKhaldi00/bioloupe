from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceeded
from app.services.rate_limiter import RateLimiter


class ThrottlingService:
    def __init__(
        self,
        limiter: RateLimiter | None = None,
        settings=None,
    ) -> None:
        self._limiter = limiter or RateLimiter()
        self._settings = settings or get_settings()

    async def enforce_user(
        self,
        user_id: str,
        limit: int | None = None,
        window: int | None = None,
    ) -> dict[str, int]:
        limit = limit or self._settings.rate_limit_per_user
        window = window or self._settings.rate_limit_window_seconds
        key = f"rate_limit:user:{user_id}"
        result = await self._limiter.check(key, limit, window)
        if not result.allowed:
            raise RateLimitExceeded(result.remaining, result.reset_in)
        return {
            "remaining": result.remaining,
            "limit": limit,
            "reset_in": result.reset_in,
        }
