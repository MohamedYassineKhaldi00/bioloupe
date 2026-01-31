from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import TeamRole


class TeamCreate(BaseModel):
    name: str
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    role: TeamRole
    member_count: int


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: TeamRole
    joined_at: datetime


class TeamMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: TeamRole = TeamRole.member


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamInvitationCreate(BaseModel):
    email: EmailStr
    role: TeamRole = TeamRole.member


class TeamInvitationAccept(BaseModel):
    token: str
