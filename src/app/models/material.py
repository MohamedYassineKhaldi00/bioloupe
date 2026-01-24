from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.session import Session
    from app.models.user import User


class MaterialType(str, enum.Enum):
    paper = "paper"
    sequence = "sequence"
    image = "image"
    experiment = "experiment"
    note = "note"


class Material(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    material_type: Mapped[MaterialType] = mapped_column(
        Enum(MaterialType, name="material_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    qdrant_point_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    session: Mapped["Session"] = relationship(back_populates="materials")
    uploaded_by: Mapped["User"] = relationship(back_populates="materials_uploaded")

    __table_args__ = (
        Index("ix_materials_session_type", "session_id", "material_type"),
        Index("ix_materials_uploaded_by", "uploaded_by_id"),
        Index("ix_materials_qdrant_point", "qdrant_point_id"),
    )
