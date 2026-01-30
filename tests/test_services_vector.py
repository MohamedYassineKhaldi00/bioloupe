import pytest
import numpy as np

from app.services.vector_service import VectorService
from app.core.vector_exceptions import VectorDimensionMismatch


class DummyClient:
    async def upsert(self, *a, **k):
        class R:
            status = "completed"

        return R()


class DummyWrapper:
    def __init__(self):
        self.client = DummyClient()

    async def with_retry(self, operation, *args, **kwargs):
        return await operation(*args, **kwargs)


@pytest.mark.asyncio
async def test_upsert_vector_success(monkeypatch):
    monkeypatch.setattr("app.services.vector_service.get_qdrant_client", lambda: DummyWrapper())
    svc = VectorService()
    vec = np.zeros(768)
    payload = {
        "material_id": "m1",
        "session_id": "s1",
        "team_id": "t1",
        "modality": "paper",
        "title": "T",
    }
    ok = await svc.upsert_vector("bioloupe_unified", "m1", vec, payload)
    assert ok is True


@pytest.mark.asyncio
async def test_upsert_vector_dimension_mismatch(monkeypatch):
    monkeypatch.setattr("app.services.vector_service.get_qdrant_client", lambda: DummyWrapper())
    svc = VectorService()
    vec = np.zeros(10)
    payload = {
        "material_id": "m1",
        "session_id": "s1",
        "team_id": "t1",
        "modality": "paper",
    }
    with pytest.raises(VectorDimensionMismatch):
        await svc.upsert_vector("bioloupe_unified", "m1", vec, payload)
