from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class TopicSubscription(Base):
    __tablename__ = "topic_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords: Mapped[dict | None] = mapped_column("keywords", nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(nullable=True)
