from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models import SessionPermission


class SessionCreate(BaseModel):
    team_id: str
    title: str
    description: str | None = None
    topic_tags: list[str] = Field(default_factory=list)


class SessionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    topic_tags: list[str] | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    team_id: str
    title: str
    description: str | None = None
    topic_tags: list[str]
    created_by_id: str | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class SessionListResponse(BaseModel):
    id: str
    team_id: str
    title: str
    description: str | None = None
    topic_tags: list[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class SessionParticipantCreate(BaseModel):
    user_id: str
    permission: SessionPermission


class SessionParticipantUpdate(BaseModel):
    permission: SessionPermission


class SessionParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: str
    permission: SessionPermission
    joined_at: datetime


class SessionStats(BaseModel):
    material_counts: dict[str, int]
    participant_count: int
    activity_count: int


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: str | None = None
    action_type: str
    entity_type: str
    entity_id: str
    details: dict | None = None
    timestamp: datetime


class SessionSearchParams(BaseModel):
    query: str
    team_id: str | None = None
    include_archived: bool = False
