from __future__ import annotations

import uuid
from typing import Annotated, List, Tuple
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..models.user import User
from ..models.team import TeamMember, TeamRole
from ..models.session import Session, SessionPermission
from ..services.permission_service import PermissionService
from ..services.cache_service import CacheService
from .auth import get_current_active_user


async def get_permission_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PermissionService:
    return PermissionService(db)


async def get_cache_service() -> CacheService:
    return CacheService()


async def require_team_permission(
    team_id: str,
    required_roles: List[TeamRole],
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> TeamMember:
    team_uuid = uuid.UUID(team_id)
    cache_key = f"team_role:{team_id}:{current_user.id}"

    cached_role = await cache_service.get(cache_key)
    if cached_role:
        membership = await permission_service.get_team_membership(
            team_uuid, current_user.id
        )
        if membership and membership.role.value == cached_role:
            if membership.role not in required_roles:
                from ..core.exceptions import PermissionDenied
                raise PermissionDenied(
                    "Insufficient team permissions",
                    required_permission=f"Team role must be one of: {', '.join([r.value for r in required_roles])}"
                )
            return membership

    membership = await permission_service.verify_team_permission(
        team_uuid, current_user.id, required_roles
    )
    await cache_service.set(cache_key, membership.role.value, ttl=300)

    return membership


async def require_team_owner(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> TeamMember:
    return await require_team_permission(
        team_id=team_id,
        required_roles=[TeamRole.owner],
        current_user=current_user,
        permission_service=permission_service,
        cache_service=cache_service
    )


async def require_team_admin(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> TeamMember:
    return await require_team_permission(
        team_id=team_id,
        required_roles=[TeamRole.owner, TeamRole.admin],
        current_user=current_user,
        permission_service=permission_service,
        cache_service=cache_service
    )


async def require_session_permission(
    session_id: str,
    required_permissions: List[SessionPermission],
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> Session:
    session_uuid = uuid.UUID(session_id)
    cache_key = f"session_permission:{session_id}:{current_user.id}"

    cached_permission = await cache_service.get(cache_key)
    if cached_permission:
        session, user_permission_value = cached_permission, SessionPermission(cached_permission)
        if user_permission_value not in required_permissions:
            from ..core.exceptions import PermissionDenied
            raise PermissionDenied(
                "Insufficient session permissions",
                required_permission=f"Session permission must be one of: {', '.join([p.value for p in required_permissions])}"
            )
        session = await permission_service.get_session_with_team(session_uuid)
        if session:
            return session

    session = await permission_service.verify_session_permission(
        session_uuid, current_user.id, required_permissions
    )
    _, user_permission = await permission_service.resolve_session_permission(
        session_uuid, current_user.id
    )
    await cache_service.set(cache_key, user_permission.value, ttl=300)

    return session


async def get_session_with_permission(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)]
) -> Tuple[Session, SessionPermission]:
    session_uuid = uuid.UUID(session_id)
    cache_key = f"session_permission:{session_id}:{current_user.id}"

    cached_permission = await cache_service.get(cache_key)

    session, user_permission = await permission_service.resolve_session_permission(
        session_uuid, current_user.id
    )

    if cached_permission is None:
        await cache_service.set(cache_key, user_permission.value, ttl=300)

    return session, user_permission
