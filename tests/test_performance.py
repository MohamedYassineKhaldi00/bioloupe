import pytest
from types import SimpleNamespace

from app.api.v1.endpoints.performance import CacheMetricsResponse, QueryExplainRequest, QueryExplainResponse, cache_metrics, explain_query, vector_metrics
from app.services.performance_cache import PerformanceCacheService
from app.services.throttling_service import ThrottlingService
from app.services.vector_optimization import VectorOptimizationService
from app.core.exceptions import RateLimitExceeded


class DummyCache:
    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ttl):
        self._data[key] = value

    async def delete(self, key):
        self._data.pop(key, None)

    async def invalidate_prefix(self, prefix):
        for key in list(self._data):
            if key.startswith(prefix):
                self._data.pop(key, None)


class DummyRedis:
    async def hgetall(self, key):
        return {"hit": "1", "miss": "0"}


class DummySettings:
    vector_search_cache_ttl_seconds = 1
    embedding_cache_ttl_seconds = 1
    rate_limit_window_seconds = 1
    rate_limit_per_user = 1
    slow_query_threshold_ms = 1


class DummyQdrant:
    class DummyPoint:
        def __init__(self):
            self.payload = {"material_id": "m1"}
            self.score = 0.9
            self.id = "point"

    async def search_vectors(self, collection, query_vector, limit=10):
        return [self.DummyPoint()]

    async def update_collection_config(self, *args, **kwargs):
        self.updated = True

    async def collection_info(self, collection):
        return SimpleNamespace(config=SimpleNamespace(json=lambda: {"collection": collection}))

    async def collection_stats(self, collection):
        return SimpleNamespace(vectors_count=1, optimizers_config=None)


class DummyLimiter:
    def __init__(self, allowed: bool):
        self.allowed = allowed

    async def check(self, key, limit, window):
        class Result:
            def __init__(self, allowed, remaining, reset):
                self.allowed = allowed
                self.remaining = remaining
                self.reset_in = reset

        remaining = 0 if not self.allowed else max(limit - 1, 0)
        return Result(self.allowed, remaining, 10)


@pytest.mark.asyncio
async def test_performance_cache_service():
    cache = DummyCache()
    settings = DummySettings()
    service = PerformanceCacheService(cache=cache, redis_client=DummyRedis(), settings=settings)
    await service.cache_embedding_vector("id", [0.1], 1, ttl=1)
    assert (await service.get_cached_embedding("id", 1))["version"] == 1
    await service.invalidate_embedding_cache("id")
    assert await service.get_cached_embedding("id", 1) is None
    await service.cache_vector_search("materials", [0.1], [{"score": 1}], ttl=1)
    assert await service.get_vector_search("materials", [0.1]) == [{"score": 1}]


@pytest.mark.asyncio
async def test_vector_optimization_service_caches():
    settings = DummySettings()
    cache = PerformanceCacheService(cache=DummyCache(), redis_client=DummyRedis(), settings=settings)
    service = VectorOptimizationService(DummyQdrant(), cache, settings=settings)
    data, from_cache = await service.search_with_cache("coll", [0.2])
    assert not from_cache
    data, from_cache = await service.search_with_cache("coll", [0.2])
    assert from_cache
    stats = await service.monitor_collection("coll")
    assert stats["collection"] == "coll"


@pytest.mark.asyncio
async def test_throttling_service_limits():
    limiter = DummyLimiter(False)
    throttler = ThrottlingService(limiter, settings=DummySettings())
    with pytest.raises(RateLimitExceeded):
        await throttler.enforce_user("user")


@pytest.mark.asyncio
async def test_performance_router_endpoints():
    settings = DummySettings()
    cache_service = PerformanceCacheService(cache=DummyCache(), redis_client=DummyRedis(), settings=settings)
    throttler = ThrottlingService(DummyLimiter(True), settings=settings)
    user = SimpleNamespace(id="user")
    cache_result = await cache_metrics(cache=cache_service, throttler=throttler, user=user)
    assert isinstance(cache_result, CacheMetricsResponse)

    vector_service = VectorOptimizationService(DummyQdrant(), cache_service, settings=settings)
    await vector_metrics("coll", service=vector_service, throttler=throttler, user=user)

    class FakeSession:
        async def execute(self, stmt):
            class Result:
                def all(self):
                    return ["plan"]
            return Result()

    monitor_service = SimpleNamespace(explain=lambda session, sql: ["plan"])
    resp = await explain_query(
        QueryExplainRequest(sql="SELECT 1"),
        session=FakeSession(),
        service=monitor_service,
        throttler=throttler,
        user=user,
    )
    assert isinstance(resp, QueryExplainResponse)
