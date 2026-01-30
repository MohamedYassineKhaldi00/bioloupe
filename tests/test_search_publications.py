import pytest
from types import SimpleNamespace

from app.search.models.publication_models import (
    PublicationQuerySource,
    PublicationSearchRequest,
    SavePublicationSearchRequest,
)
from app.search.routers.publication import (
    delete_saved_search,
    list_saved_searches,
    publication_search,
    save_publication_search,
)
from app.search.services.publication_search import PublicationSearchService


class DummyCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl):
        self.value = value


class DummyVector:
    async def search_vectors(self, collection, query_vector, limit=3):
        return []


class DummyExternal:
    async def search_pubmed(self, query, page, limit):
        return [{"title": "Test", "publication_id": "1", "metadata": {"source": "pubmed"}}]

    async def search_arxiv(self, query, page, limit):
        return []


class DummyAnalytics:
    async def record_query(self, *args, **kwargs):
        return None


class DummySavedSearchService:
    async def save(self, user_id, request):
        return {
            "id": "abc",
            "name": request.name,
            "query": request.query,
            "sources": [source.value for source in request.sources],
            "filters": request.filters,
            "notify_email": request.notify_email,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

    async def list_for_user(self, user_id):
        return [
            {
                "id": "abc",
                "name": "name",
                "query": "q",
                "sources": [PublicationQuerySource.pubmed.value],
                "filters": None,
                "notify_email": False,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ]

    async def delete(self, user_id, search_id):
        self.deleted = True


@pytest.mark.asyncio
async def test_publication_search_service_returns_results():
    service = PublicationSearchService(
        cache=DummyCache(),
        vector_service=DummyVector(),
        external_client=DummyExternal(),
        analytics=DummyAnalytics(),
        saved_search=DummySavedSearchService(),
    )
    request = PublicationSearchRequest(query="cancer", page=1, limit=1)
    response = await service.search(request)
    assert response.total == 1
    assert response.results[0].title == "Test"


@pytest.mark.asyncio
async def test_publication_router_endpoints():
    class DummyService:
        async def search(self, request):
            return SimpleNamespace(total=0, results=[], __class__=SimpleNamespace)

        async def save(self, user_id, request):
            return {
                "id": "abc",
                "name": request.name,
                "query": request.query,
                "sources": [PublicationQuerySource.pubmed.value],
                "filters": None,
                "notify_email": request.notify_email,
                "created_at": "now",
                "updated_at": "now",
            }

        async def list_saved(self, user_id):
            return [
                {
                    "id": "abc",
                    "name": "name",
                    "query": "q",
                    "sources": [PublicationQuerySource.pubmed.value],
                    "filters": None,
                    "notify_email": False,
                    "created_at": "now",
                    "updated_at": "now",
                }
            ]

        async def delete_saved(self, user_id, search_id):
            return None

    user = SimpleNamespace(id="user")
    await publication_search(PublicationSearchRequest(query="a"), service=DummyService(), user=user)
    await save_publication_search(
        SavePublicationSearchRequest(name="s", query="a"),
        service=DummyService(),
        user=user,
    )
    await list_saved_searches(service=DummyService(), user=user)
    await delete_saved_search("abc", service=DummyService(), user=user)
