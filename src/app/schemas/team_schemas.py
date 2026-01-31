from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer

from app.models import TeamRole


class TeamCreate(BaseModel):
    name: str
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    name: str
    description: str | None = None
    created_by_id: str | UUID
    created_at: datetime
    updated_at: datetime

    @field_serializer("id", "created_by_id")
    def serialize_uuid(self, v: str | UUID) -> str:
        return str(v)


class TeamListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    name: str
    description: str | None = None
    role: TeamRole
    member_count: int

    @field_serializer("id")
    def serialize_uuid(self, v: str | UUID) -> str:
        return str(v)


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    team_id: str | UUID
    user_id: str | UUID
    role: TeamRole
    joined_at: datetime

    @field_serializer("id", "team_id", "user_id")
    def serialize_uuid(self, v: str | UUID) -> str:
        return str(v)


class TeamMemberCreate(BaseModel):
    user_id: str
    role: TeamRole = TeamRole.member


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamInvitationCreate(BaseModel):
    email: EmailStr
    role: TeamRole = TeamRole.member


class TeamInvitationAccept(BaseModel):
    token: str
