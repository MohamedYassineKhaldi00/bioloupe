from __future__ import annotations

from pydantic import BaseModel, Field
from app.models.material import MaterialType


class InitiateUploadRequest(BaseModel):
    team_id: str
    session_id: str
    material_id: str
    material_type: MaterialType
    filename: str
    content_type: str
    file_size: int = Field(..., ge=1)
    checksum: str | None = None


class PresignedPart(BaseModel):
    part_number: int
    url: str


class InitiateUploadResponse(BaseModel):
    bucket: str
    object_key: str
    upload_id: str | None = None
    presigned_url: str | None = None
    parts: list[PresignedPart] | None = None


class CompleteMultipartUploadPart(BaseModel):
    part_number: int
    etag: str


class CompleteMultipartUploadRequest(BaseModel):
    bucket: str
    object_key: str
    upload_id: str
    parts: list[CompleteMultipartUploadPart]
    checksum: str | None = None


class CompleteMultipartUploadResponse(BaseModel):
    file_url: str
    checksum: str | None = None


class PresignedDownloadRequest(BaseModel):
    bucket: str
    object_key: str


class PresignedDownloadResponse(BaseModel):
    url: str
