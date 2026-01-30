import pytest
import asyncio
from unittest.mock import AsyncMock
from app.utils.retry import retry


@pytest.mark.asyncio
async def test_retry_async_succeeds_after_retries():
    calls = {"count": 0}

    @retry(max_retries=3, base_delay=0.01)
    async def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise Exception("fail")
        return "ok"

    res = await flaky()
    assert res == "ok"
    assert calls["count"] == 2


def test_retry_sync_succeeds_after_retries():
    calls = {"count": 0}

    @retry(max_retries=3, base_delay=0.01)
    def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise Exception("fail")
        return "ok"

    res = flaky()
    assert res == "ok"
    assert calls["count"] == 2
