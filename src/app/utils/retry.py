from __future__ import annotations

import asyncio
import functools
from typing import Callable, Iterable, Type, Any


def retry(
    max_retries: int = 3,
    exceptions: Iterable[Type[BaseException]] = (Exception,),
    base_delay: float = 0.5
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exc = None
                for attempt in range(1, max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except tuple(exceptions) as exc:
                        last_exc = exc
                        if attempt == max_retries:
                            raise
                        await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
                raise last_exc
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exc = None
                for attempt in range(1, max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except tuple(exceptions) as exc:
                        last_exc = exc
                        if attempt == max_retries:
                            raise
                        import time
                        time.sleep(base_delay * (2 ** (attempt - 1)))
                raise last_exc
            return sync_wrapper
    return decorator
