from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...app.db.base import get_db
from ...app.models.user import User
from ...app.models.team import TeamMember, TeamRole
from ...app.api.dependencies.auth import get_current_active_user
from ...app.api.dependencies.permissions import (
    require_team_owner,
    require_team_admin,
    require_team_permission
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    membership: Annotated[TeamMember, Depends(
        lambda tid, user, svc, cache: require_team_permission(
            tid,
            [TeamRole.owner, TeamRole.admin, TeamRole.member, TeamRole.viewer],
            user, svc, cache
        )
    )],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "team_id": team_id,
        "user_role": membership.role.value,
        "message": "Team retrieved successfully"
    }


@router.post("/{team_id}/members")
async def add_team_member(
    team_id: str,
    membership: Annotated[TeamMember, Depends(require_team_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "team_id": team_id,
        "message": "Member added successfully"
    }


@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    membership: Annotated[TeamMember, Depends(require_team_admin)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "team_id": team_id,
        "user_id": user_id,
        "message": "Member removed successfully"
    }


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    membership: Annotated[TeamMember, Depends(require_team_owner)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    return {
        "team_id": team_id,
        "message": "Team deleted successfully"
    }
