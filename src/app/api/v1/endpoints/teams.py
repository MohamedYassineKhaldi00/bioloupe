from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.permissions import require_team_permission, team_role_required
from app.core.exceptions import PermissionDenied
from app.db.base import get_db
from app.models import TeamRole, User
from app.models import TeamMember
from app.schemas.team_schemas import (
    TeamCreate,
    TeamInvitationAccept,
    TeamInvitationCreate,
    TeamListResponse,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamMemberUpdate,
    TeamResponse,
    TeamUpdate,
)
from app.services.invitation_service import InvitationPayload, InvitationService
from app.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamResponse)
async def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    service = TeamService(db)
    team = await service.create_team(payload.name, payload.description, str(current_user.id))
    return TeamResponse.model_validate(team)


@router.get("", response_model=list[TeamListResponse])
async def list_teams(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[TeamListResponse]:
    service = TeamService(db)
    rows = await service.list_teams_for_user(str(current_user.id))
    return [TeamListResponse(**row) for row in rows]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    _member=Depends(team_role_required([TeamRole.owner, TeamRole.admin, TeamRole.member, TeamRole.viewer])),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    service = TeamService(db)
    team = await service.get_team(team_id)
    return TeamResponse.model_validate(team)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    payload: TeamUpdate,
    _member=Depends(team_role_required([TeamRole.owner, TeamRole.admin])),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    service = TeamService(db)
    team = await service.update_team(team_id, payload.name, payload.description)
    return TeamResponse.model_validate(team)


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    _member=Depends(team_role_required([TeamRole.owner])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = TeamService(db)
    await service.delete_team(team_id)
    return {"status": "deleted"}


@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def add_member(
    team_id: str,
    payload: TeamMemberCreate,
    _member=Depends(team_role_required([TeamRole.owner, TeamRole.admin])),
    db: AsyncSession = Depends(get_db),
) -> TeamMemberResponse:
    service = TeamService(db)
    added = await service.add_member(team_id, payload.user_id, payload.role)
    return TeamMemberResponse.model_validate(added)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: str,
    _member=Depends(team_role_required([TeamRole.owner, TeamRole.admin, TeamRole.member, TeamRole.viewer])),
    db: AsyncSession = Depends(get_db),
) -> list[TeamMemberResponse]:
    service = TeamService(db)
    members = await service.list_members(team_id)
    return [TeamMemberResponse(**member) for member in members]


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_member(
    team_id: str,
    user_id: str,
    payload: TeamMemberUpdate,
    current_member=Depends(team_role_required([TeamRole.owner, TeamRole.admin])),
    db: AsyncSession = Depends(get_db),
) -> TeamMemberResponse:
    service = TeamService(db)
    target = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    target_member = target.scalar_one_or_none()
    if target_member and target_member.role == TeamRole.owner and current_member.role != TeamRole.owner:
        raise PermissionDenied("Cannot modify team owner")
    member = await service.update_member_role(team_id, user_id, payload.role)
    return TeamMemberResponse.model_validate(member)


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = TeamService(db)
    if user_id != str(current_user.id):
        await require_team_permission(team_id, [TeamRole.owner, TeamRole.admin], current_user, db)
        result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member and member.role == TeamRole.owner:
            raise PermissionDenied("Cannot remove team owner")
    await service.remove_member(team_id, user_id)
    return {"status": "removed"}


@router.post("/{team_id}/invitations")
async def create_invitation(
    team_id: str,
    payload: TeamInvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await require_team_permission(team_id, [TeamRole.owner, TeamRole.admin], current_user, db)
    service = InvitationService()
    token = await service.create_invitation(
        InvitationPayload(
            team_id=team_id,
            email=payload.email,
            role=payload.role,
            invited_by=str(current_user.id),
        )
    )
    return {"token": token}


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    invitation = await InvitationService().consume_invitation(token)
    if invitation.email.lower() != current_user.email.lower():
        raise PermissionDenied("Invitation does not match user")
    service = TeamService(db)
    await service.add_member(invitation.team_id, str(current_user.id), invitation.role)
    return {"status": "accepted"}
