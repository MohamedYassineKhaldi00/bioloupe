from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    full_name: str
    orcid_id: str | None = None

    @field_serializer("id")
    def serialize_id(self, v: str | UUID) -> str:
        return str(v)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | UUID
    email: EmailStr
    full_name: str
    orcid_id: str | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("id")
    def serialize_id(self, v: str | UUID) -> str:
        return str(v)


class UserUpdate(BaseModel):
    full_name: str | None = None
    orcid_id: str | None = None
