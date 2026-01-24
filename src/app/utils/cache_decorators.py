from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from app.services.cache_service import CacheService

P = ParamSpec("P")
R = TypeVar("R")


def _build_cache_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    payload = json.dumps({"args": args, "kwargs": kwargs}, default=str, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def cached(ttl: int, key_prefix: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cache = CacheService()
            key = _build_cache_key(key_prefix, args, kwargs)
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value  # type: ignore[return-value]

            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator
