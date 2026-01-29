from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class YjsSyncStep1Event(BaseModel):
    """Client sends state vector to start sync."""

    material_id: UUID = Field(..., description="Material document ID")
    state_vector: str = Field(
        ...,
        description="Hex-encoded Y.js state vector"
    )


class YjsSyncStep2Event(BaseModel):
    """Server responds with missing updates."""

    material_id: UUID
    update: str = Field(..., description="Hex-encoded Y.js update")


class YjsUpdateEvent(BaseModel):
    """Client sends document update."""

    material_id: UUID
    update: str = Field(..., description="Hex-encoded Y.js update bytes")


class YjsUpdateBroadcast(BaseModel):
    """Server broadcasts update to other clients."""

    material_id: UUID
    update: str
    origin: UUID = Field(..., description="User who made the update")


class YjsAwarenessUpdateEvent(BaseModel):
    """Awareness protocol update (cursor, selection)."""

    material_id: UUID
    awareness_update: str = Field(
        ...,
        description="Hex-encoded awareness update"
    )


class YjsAwarenessBroadcast(BaseModel):
    """Broadcast awareness to other clients."""

    material_id: UUID
    awareness_update: str
    user_id: UUID


class MaterialSubscribeEvent(BaseModel):
    """Subscribe to material for collaborative editing."""

    material_id: UUID


class MaterialUnsubscribeEvent(BaseModel):
    """Unsubscribe from material."""

    material_id: UUID


class YjsDocumentState(BaseModel):
    """Full Y.js document state for snapshots."""

    material_id: UUID
    state: str = Field(..., description="Hex-encoded state")
    version: int = Field(default=1, description="Schema version")
    created_at: datetime
    updated_at: datetime


class YjsErrorEvent(BaseModel):
    """CRDT-specific error event."""

    type: str = "crdt_error"
    message: str
    material_id: UUID | None = None
    code: str | None = None
