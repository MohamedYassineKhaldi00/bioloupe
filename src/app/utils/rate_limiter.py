from __future__ import annotations

import asyncio
import time
from typing import Optional


class RateLimiter:
    def __init__(self, requests_per_second: float, capacity: Optional[int] = None):
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be > 0")
        self.rps = float(requests_per_second)
        self.capacity = capacity or max(1, int(self.rps))
        self._tokens = float(self.capacity)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last
        refill = elapsed * self.rps
        if refill > 0:
            self._tokens = min(self.capacity, self._tokens + refill)
            self._last = now

    async def acquire(self):
        async with self._lock:
            await self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return
            # wait until at least one token is available
            needed = 1 - self._tokens
            wait_time = needed / self.rps
            await asyncio.sleep(wait_time)
            await self._refill()
            self._tokens = max(0.0, self._tokens - 1)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False
