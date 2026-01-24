from __future__ import annotations

from fastapi import APIRouter

from app.schemas.upload_schemas import (
    CompleteMultipartUploadRequest,
    CompleteMultipartUploadResponse,
    InitiateUploadRequest,
    InitiateUploadResponse,
    PresignedDownloadRequest,
    PresignedDownloadResponse,
    PresignedPart,
)
from app.services.file_validator import validate_file
from app.services.storage_service import StorageService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/initiate", response_model=InitiateUploadResponse)
async def initiate_upload(payload: InitiateUploadRequest) -> InitiateUploadResponse:
    validate_file(payload.filename, payload.content_type, payload.file_size, payload.material_type)

    storage = StorageService()
    bucket = storage.bucket_for_material(payload.material_type)
    key = storage.build_object_key(
        payload.team_id, payload.session_id, payload.material_id, payload.filename
    )

    presigned_url, upload_id, part_urls = await storage.presign_upload_or_multipart(
        bucket=bucket,
        key=key,
        content_type=payload.content_type,
        file_size=payload.file_size,
    )

    parts = None
    if part_urls:
        parts = [PresignedPart(part_number=part, url=url) for part, url in part_urls]

    return InitiateUploadResponse(
        bucket=bucket,
        object_key=key,
        upload_id=upload_id,
        presigned_url=presigned_url,
        parts=parts,
    )


@router.post("/complete", response_model=CompleteMultipartUploadResponse)
async def complete_upload(payload: CompleteMultipartUploadRequest) -> CompleteMultipartUploadResponse:
    storage = StorageService()
    parts_payload = [
        {"PartNumber": part.part_number, "ETag": part.etag} for part in payload.parts
    ]
    file_url = await storage.complete_multipart_upload(
        bucket=payload.bucket,
        key=payload.object_key,
        upload_id=payload.upload_id,
        parts=parts_payload,
    )
    return CompleteMultipartUploadResponse(file_url=file_url, checksum=payload.checksum)


@router.post("/presigned-download", response_model=PresignedDownloadResponse)
async def presigned_download(payload: PresignedDownloadRequest) -> PresignedDownloadResponse:
    storage = StorageService()
    url = await storage.generate_presigned_download(payload.bucket, payload.object_key)
    return PresignedDownloadResponse(url=url)
