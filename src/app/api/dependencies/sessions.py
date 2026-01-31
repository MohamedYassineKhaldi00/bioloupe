from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
import uuid
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.core.exceptions import PermissionDenied, SessionNotFound
from app.db.base import get_db
from app.models import Session, SessionParticipant, SessionPermission

PERMISSION_ORDER = {
    SessionPermission.read: 1,
    SessionPermission.write: 2,
    SessionPermission.admin: 3,
}


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


async def get_session(session_id: str | uuid.UUID, db: AsyncSession = Depends(get_db)) -> Session:
    session_uuid = _as_uuid(session_id)
    session = await db.get(Session, session_uuid)
    if not session or session.deleted_at is not None:
        raise SessionNotFound(str(session_id))
    return session


async def require_session_permission(
    session_id: str | uuid.UUID,
    required_permissions: Iterable[SessionPermission],
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Session:
    session_uuid = _as_uuid(session_id)
    session = await db.get(Session, session_uuid)
    if not session or session.deleted_at is not None:
        raise SessionNotFound(str(session_id))

    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_uuid,
            SessionParticipant.user_id == current_user.id,
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise PermissionDenied("Insufficient permissions")

    required_level = max(PERMISSION_ORDER[p] for p in required_permissions)
    current_level = PERMISSION_ORDER[participant.permission]
    if current_level < required_level:
        raise PermissionDenied("Insufficient permissions")

    return session


def session_permission_required(required_permissions: Iterable[SessionPermission]):
    async def dependency(
        session_id: str | uuid.UUID,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> Session:
        return await require_session_permission(session_id, required_permissions, current_user, db)

    return dependency


async def get_session_with_permission(
    session_id: str | uuid.UUID,
    permission: SessionPermission,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Session:
    return await require_session_permission(session_id, [permission], current_user, db)
