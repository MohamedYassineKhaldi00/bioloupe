from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.team import Team, TeamMember, TeamRole
from ..models.session import Session, SessionParticipant, SessionPermission
from ..models.user import User
from ..core.exceptions import (
    TeamNotFound,
    SessionNotFound,
    NotTeamMember,
    PermissionDenied
)


class PermissionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_team_membership(
        self, team_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[TeamMember]:
        result = await self._db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .where(TeamMember.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def verify_team_membership(
        self, team_id: uuid.UUID, user_id: uuid.UUID
    ) -> TeamMember:
        membership = await self.get_team_membership(team_id, user_id)
        if membership is None:
            raise NotTeamMember(str(team_id), str(user_id))
        return membership

    async def verify_team_permission(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        required_roles: list[TeamRole]
    ) -> TeamMember:
        membership = await self.verify_team_membership(team_id, user_id)

        if membership.role not in required_roles:
            raise PermissionDenied(
                f"Insufficient team permissions",
                required_permission=f"Team role must be one of: {', '.join([r.value for r in required_roles])}"
            )

        return membership

    def check_team_role_hierarchy(
        self, user_role: TeamRole, target_role: TeamRole
    ) -> bool:
        hierarchy = {
            TeamRole.owner: 4,
            TeamRole.admin: 3,
            TeamRole.member: 2,
            TeamRole.viewer: 1
        }
        return hierarchy[user_role] >= hierarchy[target_role]

    async def get_session_participant(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[SessionParticipant]:
        result = await self._db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == session_id)
            .where(SessionParticipant.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_session_with_team(
        self, session_id: uuid.UUID
    ) -> Optional[Session]:
        result = await self._db.execute(
            select(Session)
            .options(selectinload(Session.team))
            .where(Session.id == session_id)
            .where(Session.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def resolve_session_permission(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Session, SessionPermission]:
        session = await self.get_session_with_team(session_id)
        if session is None:
            raise SessionNotFound(str(session_id))

        participant = await self.get_session_participant(session_id, user_id)
        if participant is not None:
            return session, participant.permission

        team_membership = await self.get_team_membership(
            session.team_id, user_id
        )
        if team_membership is None:
            raise PermissionDenied(
                "No access to this session",
                required_permission="Must be session participant or team member"
            )

        permission = self._map_team_role_to_session_permission(
            team_membership.role
        )
        return session, permission

    def _map_team_role_to_session_permission(
        self, team_role: TeamRole
    ) -> SessionPermission:
        mapping = {
            TeamRole.owner: SessionPermission.admin,
            TeamRole.admin: SessionPermission.admin,
            TeamRole.member: SessionPermission.write,
            TeamRole.viewer: SessionPermission.read
        }
        return mapping[team_role]

    async def verify_session_permission(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        required_permissions: list[SessionPermission]
    ) -> Session:
        session, user_permission = await self.resolve_session_permission(
            session_id, user_id
        )

        if user_permission not in required_permissions:
            raise PermissionDenied(
                "Insufficient session permissions",
                required_permission=f"Session permission must be one of: {', '.join([p.value for p in required_permissions])}"
            )

        return session

    def check_session_permission_hierarchy(
        self, user_permission: SessionPermission, target_permission: SessionPermission
    ) -> bool:
        hierarchy = {
            SessionPermission.admin: 3,
            SessionPermission.write: 2,
            SessionPermission.read: 1
        }
        return hierarchy[user_permission] >= hierarchy[target_permission]

    async def get_team_by_id(self, team_id: uuid.UUID) -> Team:
        result = await self._db.execute(
            select(Team).where(Team.id == team_id)
        )
        team = result.scalar_one_or_none()
        if team is None:
            raise TeamNotFound(str(team_id))
        return team
