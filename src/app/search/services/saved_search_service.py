from __future__ import annotations

from app.search.db.saved_search_repository import SavedSearchRepository
from app.search.models.publication_models import PublicationQuerySource, SavePublicationSearchRequest


class SavedSearchService:
    def __init__(self, repository: SavedSearchRepository) -> None:
        self._repository = repository

    async def save(self, user_id: str, request: SavePublicationSearchRequest) -> dict:
        sources = [source.value for source in request.sources]
        saved = await self._repository.create(
            user_id=user_id,
            name=request.name,
            query_text=request.query,
            filters=request.filters,
            sources=sources,
            notify_email=request.notify_email,
        )
        return self._serialize(saved)

    async def list_for_user(self, user_id: str) -> list[dict]:
        saved_items = await self._repository.list_for_user(user_id)
        return [self._serialize(item) for item in saved_items]

    async def delete(self, user_id: str, search_id: str) -> None:
        await self._repository.delete(user_id, search_id)

    def _serialize(self, entry) -> dict:
        sources = [
            PublicationQuerySource(src) if isinstance(src, str) else src
            for src in (entry.sources or [])
        ]
        return {
            "id": str(entry.id),
            "name": entry.name,
            "query": entry.query_text,
            "sources": sources,
            "filters": entry.filters,
            "notify_email": entry.notify_email,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }
