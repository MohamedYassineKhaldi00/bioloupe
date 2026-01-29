import pytest
import json

from app.services.cache_service import CacheService
from app.core.exceptions import CacheException


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.metrics = {"hit": 0, "miss": 0}

    async def get(self, key):
        return self.store.get(key)

    async def hincrby(self, name, field, amount):
        self.metrics[field] = self.metrics.get(field, 0) + amount

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def scan_iter(self, match=None):
        # simple implementation
        pattern = match.rstrip("*") if match else None
        for k in list(self.store.keys()):
            if not pattern or k.startswith(pattern):
                yield k


@pytest.mark.asyncio
async def test_get_miss_and_hit(monkeypatch):
    r = FakeRedis()
    svc = CacheService(redis=r)

    # miss
    assert await svc.get("nok") is None
    assert r.metrics["miss"] == 1

    # set and hit
    await svc.set("k", {"a": 1}, ttl=10)
    assert await svc.get("k") == {"a": 1}
    assert r.metrics["hit"] == 1


@pytest.mark.asyncio
async def test_delete_and_invalidate_prefix(monkeypatch):
    r = FakeRedis()
    r.store = {"pref:1": "x", "pref:2": "y", "other": "z"}
    svc = CacheService(redis=r)

    await svc.invalidate_prefix("pref:")
    assert "pref:1" not in r.store and "pref:2" not in r.store
    assert "other" in r.store


@pytest.mark.asyncio
async def test_get_or_set_and_warm(monkeypatch):
    r = FakeRedis()
    svc = CacheService(redis=r)

    async def loader():
        return {"loaded": True}

    val = await svc.get_or_set("gk", 10, loader)
    assert val == {"loaded": True}
    # now exists
    assert await svc.get("gk") == {"loaded": True}

    await svc.warm({"a": (1, 5), "b": ({"x": 1}, 10)})
    assert r.store.get("a") is not None and r.store.get("b") is not None


@pytest.mark.asyncio
async def test_cache_error_wrapping(monkeypatch):
    class BadRedis:
        async def get(self, key):
            raise RuntimeError("boom")

    svc = CacheService(redis=BadRedis())
    with pytest.raises(CacheException):
        await svc.get("k")
