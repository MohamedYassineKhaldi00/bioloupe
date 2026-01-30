import pytest
import numpy as np

from app.services.vector_service import VectorService


class DummyClient:
    async def upsert(self, *a, **k):
        return None

    async def delete(self, *a, **k):
        return None


class DummyWrapper:
    def __init__(self, fail_delete=False):
        self.client = DummyClient()
        self._fail_delete = fail_delete

    async def with_retry(self, operation, *args, **kwargs):
        if operation == self.client.delete and self._fail_delete:
            raise RuntimeError("delete failed")
        return await operation(*args, **kwargs)


@pytest.mark.asyncio
async def test_batch_upsert_success(monkeypatch):
    monkeypatch.setattr("app.services.vector_service.get_qdrant_client", lambda: DummyWrapper())
    svc = VectorService()
    points = []
    for i in range(50):
        points.append({
            "id": f"m{i}",
            "vector": np.zeros(768),
            "payload": {"material_id": f"m{i}", "session_id": "s1", "team_id": "t1", "modality": "paper"},
        })
    upserted = await svc.batch_upsert("bioloupe_unified", points, batch_size=25)
    assert upserted == 50


@pytest.mark.asyncio
async def test_delete_vector_success_and_failure(monkeypatch):
    monkeypatch.setattr("app.services.vector_service.get_qdrant_client", lambda: DummyWrapper())
    svc = VectorService()
    ok = await svc.delete_vector("bioloupe_unified", "m1")
    assert ok is True

    monkeypatch.setattr("app.services.vector_service.get_qdrant_client", lambda: DummyWrapper(fail_delete=True))
    svc2 = VectorService()
    ok2 = await svc2.delete_vector("bioloupe_unified", "m1")
    assert ok2 is False
