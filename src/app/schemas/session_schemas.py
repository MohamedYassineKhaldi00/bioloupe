from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models import SessionPermission


class SessionCreate(BaseModel):
    team_id: uuid.UUID
    title: str
    description: str | None = None
    topic_tags: list[str] = Field(default_factory=list)


class SessionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    topic_tags: list[str] | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    title: str
    description: str | None = None
    topic_tags: list[str]
    created_by_id: uuid.UUID | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class SessionListResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    title: str
    description: str | None = None
    topic_tags: list[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class SessionParticipantCreate(BaseModel):
    user_id: uuid.UUID
    permission: SessionPermission


class SessionParticipantUpdate(BaseModel):
    permission: SessionPermission


class SessionParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    permission: SessionPermission
    joined_at: datetime


class SessionStats(BaseModel):
    material_counts: dict[str, int]
    participant_count: int
    activity_count: int


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID | None = None
    action_type: str
    entity_type: str
    entity_id: str
    details: dict | None = None
    timestamp: datetime


class SessionSearchParams(BaseModel):
    query: str
    team_id: uuid.UUID | None = None
    include_archived: bool = False
