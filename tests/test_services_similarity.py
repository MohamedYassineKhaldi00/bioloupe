import pytest
import numpy as np

from app.services.similarity_service import SimilarityService


class DummyResult:
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


class DummyClient:
    async def search(self, *a, **k):
        return [DummyResult(0.95, {"material_id": "m1", "modality": "paper"})]


class DummyWrapper:
    def __init__(self):
        self.client = DummyClient()

    async def with_retry(self, operation, *args, **kwargs):
        return await operation(*args, **kwargs)


@pytest.mark.asyncio
async def test_search_similar_caches(monkeypatch):
    monkeypatch.setattr("app.services.similarity_service.get_qdrant_client", lambda: DummyWrapper())

    # simple in-memory cache shim
    class Cache:
        def __init__(self):
            self._d = {}

        async def get(self, k):
            return self._d.get(k)

        async def set(self, k, v, ttl=0):
            self._d[k] = v
            return True

    svc = SimilarityService(cache=Cache())
    vec = np.zeros(768)
    res = await svc.search_similar("bioloupe_unified", vec, filters={"session_id": "s1"}, limit=10)
    assert len(res) == 1
    # second call should hit cache
    res2 = await svc.search_similar("bioloupe_unified", vec, filters={"session_id": "s1"}, limit=10)
    assert res2 == res
