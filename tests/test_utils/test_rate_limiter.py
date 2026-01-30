import pytest
import asyncio
import time
from app.utils.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_enforces_limit():
    limiter = RateLimiter(requests_per_second=2)

    start_time = time.time()

    async with limiter:
        pass

    async with limiter:
        pass

    async with limiter:
        pass

    elapsed = time.time() - start_time

    assert elapsed >= 0.5


@pytest.mark.asyncio
async def test_rate_limiter_concurrent():
    limiter = RateLimiter(requests_per_second=5)

    async def task():
        async with limiter:
            await asyncio.sleep(0.01)

    start_time = time.time()
    await asyncio.gather(*[task() for _ in range(10)])
    elapsed = time.time() - start_time

    assert elapsed >= 1.0
