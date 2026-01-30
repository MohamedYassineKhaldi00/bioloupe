import pytest

from app.search.models.global_models import (
    AutocompleteResponse,
    GlobalSearchEntity,
    GlobalSearchRequest,
    GlobalSearchResponse,
    GlobalSearchResult,
)
from app.search.routers.global_search import autocomplete, global_search
from app.search.services.global_search import GlobalSearchService


class DummyAsyncSession:
    async def scalars(self, stmt):
        class DummyResult:
            def all(self):
                return []

        return DummyResult()


class DummyAnalytics:
    async def record_query(self, *args, **kwargs):
        return None


class DummyCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl):
        self.cached = value


@pytest.mark.asyncio
async def test_global_search_service_empty_response():
    svc = GlobalSearchService(DummyAsyncSession(), DummyAnalytics(), DummyCache())
    response = await svc.search(GlobalSearchRequest(query="test"))
    assert response.total == 0
    assert response.results == []


@pytest.mark.asyncio
async def test_global_search_autocomplete_returns_suggestions():
    class StubService:
        async def autocomplete(self, prefix, limit=5):
            return [f"{prefix}-suggest"]

        async def search(self, request):
            return None

    res: AutocompleteResponse = await autocomplete("test", service=StubService())
    assert res.suggestions == ["test-suggest"]


@pytest.mark.asyncio
async def test_global_search_router_invokes_service():
    class StubService:
        async def search(self, request):
            return GlobalSearchResponse(
                results=[
                    GlobalSearchResult(
                        entity_type=GlobalSearchEntity.user,
                        id="1",
                        title="Test",
                        description=None,
                        team_id=None,
                        score=1.0,
                        metadata=None,
                        explanation=None,
                    )
                ],
                total=1,
                facets={"entity_type": {"user": 1}},
                elapsed_ms=0,
            )

    class DummyUser:
        id = "123"

    req = GlobalSearchRequest(query="hero")
    resp = await global_search(req, service=StubService(), user=DummyUser())
    assert resp.total == 1
