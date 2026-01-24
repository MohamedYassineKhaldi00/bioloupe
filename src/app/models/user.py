from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from ...app.db.base import Base
from ...app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.material import Material
    from app.models.session import Session, SessionParticipant
    from app.models.team import Team, TeamMember


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    orcid_id: Mapped[str | None] = mapped_column(String(19), unique=True, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    teams_created: Mapped[list["Team"]] = relationship(
        back_populates="created_by", cascade="all, delete-orphan"
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions_created: Mapped[list["Session"]] = relationship(
        back_populates="created_by", cascade="all, delete-orphan"
    )
    session_participations: Mapped[list["SessionParticipant"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    materials_uploaded: Mapped[list["Material"]] = relationship(
        back_populates="uploaded_by", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
