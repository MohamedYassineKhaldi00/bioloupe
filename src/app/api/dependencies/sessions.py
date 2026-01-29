from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
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


async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> Session:
    session = await db.get(Session, session_id)
    if not session or session.deleted_at is not None:
        raise SessionNotFound(session_id)
    return session


async def require_session_permission(
    session_id: str,
    required_permissions: Iterable[SessionPermission],
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Session:
    session = await db.get(Session, session_id)
    if not session or session.deleted_at is not None:
        raise SessionNotFound(session_id)

    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
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
        session_id: str,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> Session:
        return await require_session_permission(session_id, required_permissions, current_user, db)

    return dependency


async def get_session_with_permission(
    session_id: str,
    permission: SessionPermission,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Session:
    return await require_session_permission(session_id, [permission], current_user, db)
