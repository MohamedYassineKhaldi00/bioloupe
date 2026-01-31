from __future__ import annotations

from fastapi import APIRouter, Depends, Query
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.permissions import require_team_permission
from app.api.dependencies.sessions import require_session_permission, session_permission_required
from app.core.exceptions import PermissionDenied
from app.db.base import get_db
from app.models import ActivityLog, Material, MaterialType, Session, SessionParticipant, SessionPermission, TeamRole, User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.session_schemas import (
    ActivityLogResponse,
    SessionCreate,
    SessionListResponse,
    SessionParticipantCreate,
    SessionParticipantResponse,
    SessionParticipantUpdate,
    SessionResponse,
    SessionStats,
    SessionUpdate,
)
from app.schemas.material_schemas import MaterialListResponse
from app.services.session_service import SessionService
from app.services.material_service import MaterialService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/search", response_model=list[SessionListResponse])
async def search_sessions(
    q: str,
    team_id: str | None = None,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[SessionListResponse]:
    session_ids_result = await db.execute(
        select(SessionParticipant.session_id).where(SessionParticipant.user_id == current_user.id)
    )
    session_ids = [row[0] for row in session_ids_result.all()]
    if not session_ids:
        return []
    service = SessionService(db)
    sessions = await service.search_sessions(q, team_id, include_archived)
    sessions = [session for session in sessions if session.id in set(session_ids)]
    return [SessionListResponse.model_validate(item) for item in sessions]


@router.get("/tags", response_model=list[str])
async def list_tags(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    result = await db.execute(
        select(SessionParticipant.session_id).where(SessionParticipant.user_id == current_user.id)
    )
    session_ids = [row[0] for row in result.all()]
    service = SessionService(db)
    return await service.list_tags(session_ids)


@router.post("", response_model=SessionResponse)
async def create_session(
    payload: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    await require_team_permission(payload.team_id, [TeamRole.owner, TeamRole.admin, TeamRole.member], current_user, db)
    service = SessionService(db)
    session = await service.create_session(payload, str(current_user.id))
    return SessionResponse.model_validate(session)


@router.get("", response_model=PaginatedResponse[SessionListResponse])
async def list_sessions(
    pagination: PaginationParams = Depends(),
    team_id: str | None = None,
    include_archived: bool = False,
    tags: list[str] | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[SessionListResponse]:
    result = await db.execute(
        select(SessionParticipant.session_id).where(SessionParticipant.user_id == current_user.id)
    )
    session_ids = [row[0] for row in result.all()]
    if not session_ids:
        return PaginatedResponse(items=[], total=0, skip=pagination.skip, limit=pagination.limit, has_more=False)
    service = SessionService(db)
    items, total_count = await service.list_sessions_paginated(
        session_ids=session_ids,
        team_id=team_id,
        include_archived=include_archived,
        tags=tags,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        items=[SessionListResponse.model_validate(item) for item in items],
        total=total_count,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=pagination.skip + len(items) < total_count,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: str,
    _session=Depends(session_permission_required([SessionPermission.read])),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    service = SessionService(db)
    session = await service.get_session(session_id)
    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    await require_session_permission(session_id, [SessionPermission.write, SessionPermission.admin], current_user, db)
    service = SessionService(db)
    session = await service.update_session(session_id, payload, str(current_user.id))
    return SessionResponse.model_validate(session)
    return {"status": "deleted"}


@router.post("/{session_id}/archive")
async def archive_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_session_permission(session_id, [SessionPermission.admin], current_user, db)
    service = SessionService(db)
    await service.archive_session(session_id, str(current_user.id))
    return {"status": "archived"}


@router.post("/{session_id}/unarchive")
async def unarchive_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_session_permission(session_id, [SessionPermission.admin], current_user, db)
    service = SessionService(db)
    await service.unarchive_session(session_id, str(current_user.id))
    return {"status": "unarchived"}


@router.post("/{session_id}/restore")
async def restore_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_session_permission(session_id, [SessionPermission.admin], current_user, db)
    service = SessionService(db)
    await service.restore_session(session_id, str(current_user.id))
    return {"status": "restored"}


@router.post("/{session_id}/participants", response_model=SessionParticipantResponse)
async def add_participant(
    session_id: str,
    payload: SessionParticipantCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionParticipantResponse:
    await require_session_permission(session_id, [SessionPermission.admin], current_user, db)
    service = SessionService(db)
    participant = await service.add_participant(session_id, payload.user_id, payload.permission)
    return SessionParticipantResponse.model_validate(participant)


@router.get("/{session_id}/participants", response_model=list[SessionParticipantResponse])
async def list_participants(
    session_id: str,
    _session=Depends(session_permission_required([SessionPermission.read])),
    db: AsyncSession = Depends(get_db),
) -> list[SessionParticipantResponse]:
    service = SessionService(db)
    participants = await service.list_participants(session_id)
    return [SessionParticipantResponse.model_validate(item) for item in participants]


@router.patch("/{session_id}/participants/{user_id}", response_model=SessionParticipantResponse)
async def update_participant(
    session_id: str,
    user_id: str,
    payload: SessionParticipantUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionParticipantResponse:
    await require_session_permission(session_id, [SessionPermission.admin], current_user, db)
    service = SessionService(db)
    participant = await service.update_participant(session_id, user_id, payload.permission)
    return SessionParticipantResponse.model_validate(participant)


@router.delete("/{session_id}/participants/{user_id}")
async def remove_participant(
    session_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_session_permission(session_id, [SessionPermission.admin], current_user, db)
    service = SessionService(db)
    await service.remove_participant(session_id, user_id)
    return {"status": "removed"}


@router.get("/{session_id}/permissions")
async def get_permissions(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    session_uuid = session_id if isinstance(session_id, uuid.UUID) else uuid.UUID(session_id)
    result = await db.execute(
        select(SessionParticipant.permission).where(
            SessionParticipant.session_id == session_uuid,
            SessionParticipant.user_id == current_user.id,
        )
    )
    permission = result.scalar_one_or_none()
    if not permission:
        raise PermissionDenied("No permissions for session")
    return {"permission": permission}


@router.get("/{session_id}/activity", response_model=PaginatedResponse[ActivityLogResponse])
async def get_activity_log(
    session_id: str,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ActivityLogResponse]:
    await require_session_permission(session_id, [SessionPermission.read], current_user, db)
    session_uuid = session_id if isinstance(session_id, uuid.UUID) else uuid.UUID(session_id)
    total = await db.execute(
        select(func.count(ActivityLog.id)).where(ActivityLog.session_id == session_uuid)
    )
    total_count = total.scalar_one()
    activity_result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.session_id == session_uuid)
        .order_by(ActivityLog.timestamp.desc())
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    items = activity_result.scalars().all()
    return PaginatedResponse(
        items=[ActivityLogResponse.model_validate(item) for item in items],
        total=total_count,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=pagination.skip + len(items) < total_count,
    )


@router.get("/{session_id}/stats", response_model=SessionStats)
async def session_stats(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStats:
    await require_session_permission(session_id, [SessionPermission.read], current_user, db)
    service = SessionService(db)
    stats = await service.session_stats(session_id)
    return SessionStats(**stats)


@router.get("/{session_id}/materials", response_model=PaginatedResponse[MaterialListResponse])
async def list_session_materials(
    session_id: str,
    pagination: PaginationParams = Depends(),
    material_type: MaterialType | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MaterialListResponse]:
    await require_session_permission(session_id, [SessionPermission.read], current_user, db)
    material_service = MaterialService(db)
    items, total_count = await material_service.list_materials_paginated(
        session_id=session_id,
        material_type=material_type,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        items=[MaterialListResponse.model_validate(item) for item in items],
        total=total_count,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=pagination.skip + len(items) < total_count,
    )


@router.get("/{session_id}/materials/tags", response_model=list[str])
async def list_material_tags(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    await require_session_permission(session_id, [SessionPermission.read], current_user, db)
    session_uuid = session_id if isinstance(session_id, uuid.UUID) else uuid.UUID(session_id)
    result = await db.execute(
        select(Material.metadata_).where(Material.session_id == session_uuid, Material.deleted_at.is_(None))
    )
    tags: set[str] = set()
    for metadata in result.scalars().all():
        tags.update((metadata or {}).get("tags", []))
    return sorted(tags)
