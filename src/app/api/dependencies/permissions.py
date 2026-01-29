from __future__ import annotations

from typing import Iterable
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.core.exceptions import PermissionDenied, TeamNotFound
from app.db.base import get_db
from app.models import Team, TeamMember, TeamRole

ROLE_ORDER = {
    TeamRole.owner: 4,
    TeamRole.admin: 3,
    TeamRole.member: 2,
    TeamRole.viewer: 1,
}


async def require_team_permission(
    team_id: str,
    required_roles: Iterable[TeamRole] | None = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TeamMember:
    team = await db.get(Team, team_id)
    if not team:
        raise TeamNotFound(team_id)

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
        )
    )
    member = result.scalar_one_or_none()
    roles = set(required_roles) if required_roles is not None else set(TeamRole)
    if not member or member.role not in roles:
        raise PermissionDenied("Insufficient permissions")
    return member


def team_role_required(required_roles: Iterable[TeamRole]):
    async def dependency(
        team_id: str,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> TeamMember:
        return await require_team_permission(team_id, required_roles, current_user, db)

    return dependency


def has_required_role(member: TeamMember, required_roles: Iterable[TeamRole]) -> bool:
    return member.role in set(required_roles)


def is_owner(member: TeamMember) -> bool:
    return member.role == TeamRole.owner
