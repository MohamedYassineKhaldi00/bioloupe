from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import PermissionDenied, SessionNotFound
from app.models import ActivityLog, Material, Session, SessionParticipant, SessionPermission
from app.services.activity_service import ActivityService
from app.utils.search import build_search_filter


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.activity = ActivityService(db)

    @staticmethod
    def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)

    @staticmethod
    def _as_uuid_list(values: list[str] | list[uuid.UUID]) -> list[uuid.UUID]:
        return [value if isinstance(value, uuid.UUID) else uuid.UUID(value) for value in values]

    async def create_session(self, data, user_id: str) -> Session:
        owner_id = self._as_uuid(user_id)
        team_id = self._as_uuid(data.team_id)
        session = Session(
            id=uuid.uuid4(),
            team_id=team_id,
            title=data.title,
            description=data.description,
            topic_tags=data.topic_tags,
            created_by_id=owner_id,
        )
        self.db.add(session)
        await self.db.flush()

        participant = SessionParticipant(
            id=uuid.uuid4(),
            session_id=session.id,
            user_id=owner_id,
            permission=SessionPermission.admin,
        )
        self.db.add(participant)
        await self.activity.log(str(session.id), user_id, "created", "session", str(session.id))
        return session

    async def list_sessions_paginated(
        self,
        session_ids: list[str] | list[uuid.UUID],
        team_id: str | uuid.UUID | None,
        include_archived: bool,
        tags: list[str] | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Session], int]:
        session_uuid_ids = self._as_uuid_list(session_ids)
        query = select(Session).where(Session.deleted_at.is_(None))
        query = query.where(Session.id.in_(session_uuid_ids))
        if team_id:
            query = query.where(Session.team_id == self._as_uuid(team_id))
        if not include_archived:
            query = query.where(Session.is_archived.is_(False))
        if tags:
            query = query.where(Session.topic_tags.contains(tags))
        total = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total_count = total.scalar_one()
        result = await self.db.execute(
            query.order_by(Session.updated_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all(), total_count

    async def get_session(self, session_id: str) -> Session:
        session = await self.db.get(Session, self._as_uuid(session_id))
        if not session or session.deleted_at is not None:
            raise SessionNotFound(session_id)
        return session

    async def update_session(self, session_id: str, data, user_id: str) -> Session:
        session = await self.get_session(session_id)
        if data.title is not None:
            session.title = data.title
        if data.description is not None:
            session.description = data.description
        if data.topic_tags is not None:
            session.topic_tags = data.topic_tags
        await self.activity.log(session_id, user_id, "updated", "session", session_id)
        await self.db.flush()
        return session

    async def archive_session(self, session_id: str, user_id: str) -> Session:
        session = await self.get_session(session_id)
        session.is_archived = True
        await self.activity.log(session_id, user_id, "archived", "session", session_id)
        await self.db.flush()
        return session

    async def unarchive_session(self, session_id: str, user_id: str) -> Session:
        session = await self.get_session(session_id)
        session.is_archived = False
        await self.activity.log(session_id, user_id, "updated", "session", session_id)
        await self.db.flush()
        return session

    async def soft_delete_session(self, session_id: str, user_id: str) -> None:
        session = await self.get_session(session_id)
        session.deleted_at = datetime.now(timezone.utc)
        await self.activity.log(session_id, user_id, "deleted", "session", session_id)
        await self.db.flush()

    async def restore_session(self, session_id: str, user_id: str) -> Session:
        session = await self.get_session(session_id)
        if session.deleted_at is None:
            return session
        if session.deleted_at < datetime.now(timezone.utc) - timedelta(days=30):
            raise PermissionDenied("Restore window expired")
        session.deleted_at = None
        await self.activity.log(session_id, user_id, "restored", "session", session_id)
        await self.db.flush()
        return session

    async def add_participant(self, session_id: str | uuid.UUID, user_id: str | uuid.UUID, permission: SessionPermission) -> SessionParticipant:
        session_uuid = self._as_uuid(session_id)
        user_uuid = self._as_uuid(user_id)
        result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_uuid,
                SessionParticipant.user_id == user_uuid,
            )
        )
        participant = result.scalar_one_or_none()
        if participant:
            participant.permission = permission
            await self.db.flush()
            await self.activity.log(str(session_uuid), str(user_uuid), "updated", "participant", str(user_uuid))
            return participant

        participant = SessionParticipant(
            id=uuid.uuid4(),
            session_id=session_uuid,
            user_id=user_uuid,
            permission=permission,
        )
        self.db.add(participant)
        await self.db.flush()
        await self.activity.log(str(session_uuid), str(user_uuid), "created", "participant", str(user_uuid))
        return participant

    async def update_participant(self, session_id: str | uuid.UUID, user_id: str | uuid.UUID, permission: SessionPermission) -> SessionParticipant:
        session_uuid = self._as_uuid(session_id)
        user_uuid = self._as_uuid(user_id)
        result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_uuid,
                SessionParticipant.user_id == user_uuid,
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise PermissionDenied("Participant not found")
        participant.permission = permission
        await self.db.flush()
        await self.activity.log(str(session_uuid), str(user_uuid), "updated", "participant", str(user_uuid))
        return participant

    async def remove_participant(self, session_id: str | uuid.UUID, user_id: str | uuid.UUID) -> None:
        session_uuid = self._as_uuid(session_id)
        user_uuid = self._as_uuid(user_id)
        result = await self.db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_uuid,
                SessionParticipant.user_id == user_uuid,
            )
        )
        participant = result.scalar_one_or_none()
        if participant:
            await self.db.delete(participant)
            await self.activity.log(str(session_uuid), str(user_uuid), "deleted", "participant", str(user_uuid))

    async def list_participants(self, session_id: str | uuid.UUID) -> list[SessionParticipant]:
        session_uuid = self._as_uuid(session_id)
        result = await self.db.execute(
            select(SessionParticipant)
            .where(SessionParticipant.session_id == session_uuid)
            .order_by(SessionParticipant.joined_at.desc())
        )
        return result.scalars().all()

    async def search_sessions(self, query: str, team_id: str | uuid.UUID | None, include_archived: bool) -> list[Session]:
        search_filter = build_search_filter(Session, query, ["title", "description"])
        stmt = select(Session).where(search_filter, Session.deleted_at.is_(None))
        if team_id:
            stmt = stmt.where(Session.team_id == self._as_uuid(team_id))
        if not include_archived:
            stmt = stmt.where(Session.is_archived.is_(False))
        result = await self.db.execute(stmt.order_by(Session.updated_at.desc()))
        return result.scalars().all()

    async def list_tags(self, user_session_ids: list[str] | list[uuid.UUID]) -> list[str]:
        if not user_session_ids:
            return []
        session_uuid_ids = self._as_uuid_list(user_session_ids)
        result = await self.db.execute(
            select(Session.topic_tags).where(Session.id.in_(session_uuid_ids))
        )
        tags: set[str] = set()
        for tag_list in result.scalars().all():
            tags.update(tag_list or [])
        return sorted(tags)

    async def session_stats(self, session_id: str | uuid.UUID) -> dict:
        session_uuid = self._as_uuid(session_id)
        material_counts = await self.db.execute(
            select(Material.material_type, func.count(Material.id))
            .where(Material.session_id == session_uuid, Material.deleted_at.is_(None))
            .group_by(Material.material_type)
        )
        counts = {str(row[0]): row[1] for row in material_counts.all()}

        participant_count = await self.db.execute(
            select(func.count(SessionParticipant.id)).where(SessionParticipant.session_id == session_uuid)
        )
        activity_count = await self.db.execute(
            select(func.count(ActivityLog.id)).where(ActivityLog.session_id == session_uuid)
        )
        return {
            "material_counts": counts,
            "participant_count": participant_count.scalar_one(),
            "activity_count": activity_count.scalar_one(),
        }
