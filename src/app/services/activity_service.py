from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog


class ActivityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        session_id: str,
        user_id: str | None,
        action_type: str,
        entity_type: str,
        entity_id: str,
        details: dict | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            id=uuid.uuid4(),
            session_id=session_id,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
