from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog


class ActivityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)

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
            session_id=self._as_uuid(session_id),
            user_id=self._as_uuid(user_id),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
