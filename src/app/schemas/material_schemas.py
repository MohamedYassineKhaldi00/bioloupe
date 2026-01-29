from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models import MaterialType


class MaterialCreate(BaseModel):
    session_id: str
    material_type: MaterialType
    title: str
    metadata: dict | None = None
    file_url: str | None = None


class MaterialUpdate(BaseModel):
    title: str | None = None
    metadata: dict | None = None


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    uploaded_by_id: str | None = None
    material_type: MaterialType
    title: str
    file_url: str | None = None
    metadata: dict | None = None
    qdrant_point_id: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class MaterialListResponse(BaseModel):
    id: str
    session_id: str
    material_type: MaterialType
    title: str
    created_at: datetime
    updated_at: datetime


class MaterialUploadInitiate(BaseModel):
    session_id: str
    material_type: MaterialType
    title: str
    filename: str
    content_type: str
    file_size: int


class MaterialUploadInitiateResponse(BaseModel):
    material_id: str
    upload_url: str | None = None
    upload_id: str | None = None
    parts: list[dict[str, str | int]] | None = None
    bucket: str
    object_key: str


class MaterialUploadComplete(BaseModel):
    checksum: str | None = None


class MaterialBatchCreate(BaseModel):
    session_id: str
    materials: list[MaterialCreate]


class MaterialBatchUpdateItem(BaseModel):
    material_id: str
    metadata: dict | None = None


class MaterialBatchUpdate(BaseModel):
    updates: list[MaterialBatchUpdateItem]


class MaterialTagUpdate(BaseModel):
    tags: list[str]


class MaterialSearchParams(BaseModel):
    query: str
    session_id: str | None = None
    material_type: MaterialType | None = None


class MaterialStats(BaseModel):
    total: int
    by_type: dict[str, int]
