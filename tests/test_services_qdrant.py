import pytest
import asyncio
from app.services.qdrant_service import QdrantService
from app.core.exceptions import VectorDBException


@pytest.mark.asyncio
async def test_upsert_vectors_raises_on_empty():
    svc = QdrantService(client_wrapper=object())
    with pytest.raises(VectorDBException):
        await svc.upsert_vectors("col", [])


@pytest.mark.asyncio
async def test_search_vectors_wraps_errors(monkeypatch):
    class FakeWrapper:
        def __init__(self):
            self.client = SimpleNamespace()

        async def with_retry(self, fn, *a, **k):
            raise RuntimeError("boom")

    from types import SimpleNamespace

    svc = QdrantService(client_wrapper=FakeWrapper())
    with pytest.raises(VectorDBException):
        await svc.search_vectors("col", [0.1, 0.2])
