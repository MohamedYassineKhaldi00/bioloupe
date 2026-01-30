from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SavedSearch


class SavedSearchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        user_id: str,
        name: str,
        query_text: str,
        filters: dict | None,
        sources: list[str] | None,
        notify_email: bool,
    ) -> SavedSearch:
        saved = SavedSearch(
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            name=name,
            query_text=query_text,
            filters=filters,
            sources=sources,
            notify_email=notify_email,
        )
        self._db.add(saved)
        await self._db.flush()
        await self._db.refresh(saved)
        return saved

    async def list_for_user(self, user_id: str) -> list[SavedSearch]:
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        stmt = select(SavedSearch).where(SavedSearch.user_id == user_uuid)
        rows = await self._db.scalars(stmt)
        return rows.all()

    async def delete(self, user_id: str, search_id: str) -> None:
        try:
            search_uuid = uuid.UUID(search_id)
        except ValueError:
            return
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        stmt = select(SavedSearch).where(
            SavedSearch.user_id == user_uuid,
            SavedSearch.id == search_uuid,
        )
        row = await self._db.scalars(stmt)
        instance = row.one_or_none()
        if instance:
            await self._db.delete(instance)
            await self._db.flush()
