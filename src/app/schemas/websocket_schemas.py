from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class JoinSessionEvent(BaseModel):
    session_id: UUID = Field(..., description="Session to join")


class LeaveSessionEvent(BaseModel):
    session_id: UUID = Field(..., description="Session to leave")


class PresenceUpdateEvent(BaseModel):
    session_id: UUID
    user_id: UUID
    status: str = Field(..., pattern="^(online|away|offline)$")
    last_seen: datetime


class CursorPositionEvent(BaseModel):
    session_id: UUID
    user_id: UUID
    x: float
    y: float
    element_id: str | None = None


class MaterialAddedEvent(BaseModel):
    session_id: UUID
    material_id: UUID
    user_id: UUID
    material_type: str
    title: str


class SelectionEvent(BaseModel):
    session_id: UUID
    user_id: UUID
    element_ids: list[str]


class HeartbeatEvent(BaseModel):
    timestamp: datetime


class ErrorEvent(BaseModel):
    type: str = "error"
    message: str
    code: str | None = None
    details: dict[str, Any] | None = None


class UserPresence(BaseModel):
    user_id: UUID
    full_name: str
    status: str
    last_seen: datetime
    sid: str


class SessionParticipants(BaseModel):
    session_id: UUID
    participants: list[UserPresence]


class CanvasActionEvent(BaseModel):
    session_id: UUID
    action: str = Field(..., pattern="^(move|resize|delete|create|update)$")
    element_id: str
    position: dict[str, float] | None = None
    size: dict[str, float] | None = None
    data: dict[str, Any] | None = None


class MaterialUpdateEvent(BaseModel):
    session_id: UUID
    material_id: UUID
    changes: dict[str, Any]


class HeartbeatRequestEvent(BaseModel):
    session_id: UUID | None = None
    timestamp: datetime | None = None


class HeartbeatAckEvent(BaseModel):
    timestamp: datetime
    status: str = "ok"
