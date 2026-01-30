import pytest
from types import SimpleNamespace

from app.search.models.similarity_models import SimilarityExplorationRequest
from app.search.routers.similarity import similarity_explore
from app.search.services.similarity_explorer import SimilarityExplorationService


class DummyVectorService:
    class DummyPoint:
        def __init__(self):
            self.payload = {"material_id": "1", "title": "A", "metadata": {"tags": ["tag"]}, "indexed_at": "2025-01-01T00:00:00Z"}
            self.score = 0.9

    async def search_vectors(self, collection, query_vector, limit=12):
        return [self.DummyPoint()]


class DummyCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl):
        self.value = value


@pytest.mark.asyncio
async def test_similarity_service_explores():
    svc = SimilarityExplorationService(DummyVectorService(), DummyCache())
    request = SimilarityExplorationRequest(collection="materials", query_vector=[0.1, 0.2])
    response = await svc.explore(request)
    assert response.total == 1
    assert response.results[0].material_id == "1"


@pytest.mark.asyncio
async def test_similarity_router_uses_service():
    class StubService:
        async def explore(self, request):
            return SimpleNamespace(total=0, results=[], temporal_summary=[], reference_material=None)

    user = SimpleNamespace(id="user")
    await similarity_explore(SimilarityExplorationRequest(collection="materials", query_vector=[0.1]), service=StubService(), user=user)
