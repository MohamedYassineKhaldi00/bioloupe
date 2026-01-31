from __future__ import annotations

import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDenied, TeamNotFound
from app.core.redis_config import CACHE_TTLS
from app.models import Team, TeamMember, TeamRole
from app.services.cache_service import CacheService


class TeamService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cache = CacheService()

    @staticmethod
    def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)

    async def create_team(self, name: str, description: str | None, user_id: str) -> Team:
        owner_id = self._as_uuid(user_id)
        team = Team(id=uuid.uuid4(), name=name, description=description, created_by_id=owner_id)
        self.db.add(team)
        await self.db.flush()

        member = TeamMember(
            id=uuid.uuid4(),
            team_id=team.id,
            user_id=owner_id,
            role=TeamRole.owner,
        )
        self.db.add(member)
        await self.db.flush()
        return team

    async def list_teams_for_user(self, user_id: str | uuid.UUID) -> list[dict]:
        user_uuid = self._as_uuid(user_id)
        count_subquery = (
            select(TeamMember.team_id, func.count(TeamMember.id).label("member_count"))
            .group_by(TeamMember.team_id)
            .subquery()
        )
        stmt = (
            select(Team, TeamMember.role, count_subquery.c.member_count)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .join(count_subquery, count_subquery.c.team_id == Team.id)
            .where(TeamMember.user_id == user_uuid)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "role": role,
                "member_count": member_count,
            }
            for team, role, member_count in rows
        ]

    async def get_team(self, team_id: str | uuid.UUID) -> Team:
        team = await self.db.get(Team, self._as_uuid(team_id))
        if not team:
            raise TeamNotFound(team_id)
        return team

    async def update_team(self, team_id: str | uuid.UUID, name: str | None, description: str | None) -> Team:
        team = await self.get_team(self._as_uuid(team_id))
        if name is not None:
            team.name = name
        if description is not None:
            team.description = description
        await self.db.flush()
        return team

    async def delete_team(self, team_id: str | uuid.UUID) -> None:
        team = await self.get_team(self._as_uuid(team_id))
        await self.db.delete(team)

    async def add_member(self, team_id: str | uuid.UUID, user_id: str | uuid.UUID, role: TeamRole) -> TeamMember:
        team_uuid = self._as_uuid(team_id)
        user_uuid = self._as_uuid(user_id)
        existing = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_uuid,
                TeamMember.user_id == user_uuid,
            )
        )
        member = existing.scalar_one_or_none()
        if member:
            member.role = role
            await self.db.flush()
            await self.cache.delete(f"team_members:{team_uuid}")
            return member

        member = TeamMember(
            id=uuid.uuid4(),
            team_id=team_uuid,
            user_id=user_uuid,
            role=role,
        )
        self.db.add(member)
        await self.db.flush()
        await self.cache.delete(f"team_members:{team_uuid}")
        return member

    async def update_member_role(self, team_id: str | uuid.UUID, user_id: str | uuid.UUID, role: TeamRole) -> TeamMember:
        team_uuid = self._as_uuid(team_id)
        user_uuid = self._as_uuid(user_id)
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_uuid,
                TeamMember.user_id == user_uuid,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise PermissionDenied("Member not found")
        member.role = role
        await self.db.flush()
        await self.cache.delete(f"team_members:{team_uuid}")
        return member

    async def remove_member(self, team_id: str | uuid.UUID, user_id: str | uuid.UUID) -> None:
        team_uuid = self._as_uuid(team_id)
        user_uuid = self._as_uuid(user_id)
        result = await self.db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_uuid,
                TeamMember.user_id == user_uuid,
            )
        )
        member = result.scalar_one_or_none()
        if member:
            await self.db.delete(member)
            await self.cache.delete(f"team_members:{team_uuid}")

    async def list_members(self, team_id: str | uuid.UUID) -> list[dict]:
        team_uuid = self._as_uuid(team_id)
        cache_key = f"team_members:{team_uuid}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_uuid)
            .order_by(TeamMember.joined_at.desc())
        )
        members = result.scalars().all()
        payload = [
            {
                "id": str(member.id),
                "team_id": str(member.team_id),
                "user_id": str(member.user_id),
                "role": member.role,
                "joined_at": member.joined_at,
            }
            for member in members
        ]
        await self.cache.set(cache_key, payload, CACHE_TTLS.team_member_list)
        return payload
