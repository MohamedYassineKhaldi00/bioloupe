import pytest

from app.services.rate_limiter import RateLimiter, RateLimitResult
from app.core.exceptions import CacheException


class FakeRedis:
    def __init__(self, ret):
        self.ret = ret

    async def eval(self, script, num_keys, key, window):
        if isinstance(self.ret, Exception):
            raise self.ret
        return self.ret


@pytest.mark.asyncio
async def test_check_allows_and_remaining():
    fake = FakeRedis((1, 59))
    rl = RateLimiter(redis=fake)
    res = await rl.check("k", 5, 60)
    assert res.allowed is True
    assert res.current == 1
    assert res.remaining == 4


@pytest.mark.asyncio
async def test_check_denied_when_over_limit():
    fake = FakeRedis((6, 30))
    rl = RateLimiter(redis=fake)
    res = await rl.check("k", 5, 60)
    assert res.allowed is False
    assert res.current == 6
    assert res.remaining == 0


@pytest.mark.asyncio
async def test_check_raises_on_exception():
    fake = FakeRedis(RuntimeError("boom"))
    rl = RateLimiter(redis=fake)
    with pytest.raises(CacheException):
        await rl.check("k", 5, 60)
