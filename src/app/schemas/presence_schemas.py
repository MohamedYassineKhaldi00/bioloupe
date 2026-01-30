from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PresenceStatus(BaseModel):
    """User presence status in a session."""

    user_id: UUID
    session_id: UUID
    status: Literal["online", "away", "offline"]
    full_name: str | None = None
    last_seen: datetime


class CursorPosition(BaseModel):
    """Real-time cursor position."""

    user_id: UUID
    session_id: UUID
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    element_id: str | None = None
    timestamp: datetime | None = None


class SelectionUpdate(BaseModel):
    """User selection update."""

    user_id: UUID
    session_id: UUID
    selected_ids: list[str]
    timestamp: datetime | None = None


class CanvasAction(BaseModel):
    """Canvas manipulation action."""

    session_id: UUID
    action: Literal["move", "resize", "delete", "create", "update"]
    element_id: str
    position: dict[str, float] | None = None
    size: dict[str, float] | None = None
    data: dict[str, Any] | None = None


class MaterialUpdate(BaseModel):
    """Material update event."""

    session_id: UUID
    material_id: UUID
    changes: dict[str, Any]
    conflict: bool = False


class SessionState(BaseModel):
    """Complete session state snapshot."""

    session_id: UUID
    participants: list[PresenceStatus]
    cursors: dict[str, CursorPosition]
    selections: dict[str, list[str]]
    timestamp: datetime


class HeartbeatRequest(BaseModel):
    """Heartbeat request from client."""

    session_id: UUID | None = None
    timestamp: datetime | None = None


class HeartbeatResponse(BaseModel):
    """Heartbeat response to client."""

    timestamp: datetime
    status: str = "ok"


class UserJoinedEvent(BaseModel):
    """Event when user joins session."""

    user_id: UUID
    session_id: UUID
    full_name: str
    timestamp: datetime


class UserLeftEvent(BaseModel):
    """Event when user leaves session."""

    user_id: UUID
    session_id: UUID
    timestamp: datetime


class ConflictEvent(BaseModel):
    """Conflict resolution event."""

    conflict_type: str
    element_id: str
    user_id: UUID
    timestamp: datetime
    data: dict[str, Any]
