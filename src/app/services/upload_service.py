from __future__ import annotations

import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MaterialNotFound, SessionNotFound, StorageException
from app.models import Material, Session
from app.services.activity_service import ActivityService
from app.services.storage_service import StorageService
from app.services.ingestion_service import MaterialIngestionService
from app.services.file_validator import validate_file

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, db: AsyncSession, storage: StorageService | None = None) -> None:
        self.db = db
        self.storage = storage or StorageService()
        self.activity = ActivityService(db)

    @staticmethod
    def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)

    async def initiate_upload(self, data, user_id: str | uuid.UUID) -> dict:
        material_id = uuid.uuid4()
        session_uuid = self._as_uuid(data.session_id)
        user_uuid = self._as_uuid(user_id)
        session = await self.db.get(Session, session_uuid)
        if not session:
            raise SessionNotFound(data.session_id)
        bucket = self.storage.bucket_for_material(data.material_type)
        key = self.storage.build_object_key(str(session.team_id), str(session_uuid), str(material_id), data.filename)

        validate_file(data.filename, data.content_type, data.file_size, data.material_type)

        presigned_url, upload_id, part_urls = await self.storage.presign_upload_or_multipart(
            bucket=bucket,
            key=key,
            content_type=data.content_type,
            file_size=data.file_size,
        )

        material = Material(
            id=material_id,
            session_id=session_uuid,
            uploaded_by_id=user_uuid,
            material_type=data.material_type,
            title=data.title,
            file_url=key,
            metadata_={"upload_status": "pending", "original_filename": data.filename},
        )
        self.db.add(material)
        await self.activity.log(str(session_uuid), str(user_uuid), "created", "material", str(material_id))
        await self.db.flush()

        return {
            "material_id": str(material_id),
            "upload_url": presigned_url,
            "upload_id": upload_id,
            "parts": [
                {"part_number": part, "url": url} for part, url in (part_urls or [])
            ]
            or None,
            "bucket": bucket,
            "object_key": key,
        }

    async def complete_upload(self, material_id: str | uuid.UUID, checksum: str | None) -> Material:
        material_uuid = self._as_uuid(material_id)
        material = await self.db.get(Material, material_uuid)
        if not material or material.deleted_at is not None:
            raise MaterialNotFound(material_id)

        if not material.file_url:
            raise StorageException("Missing file reference")

        bucket = self.storage.bucket_for_material(material.material_type)
        exists = await self.storage.file_exists(bucket, material.file_url)
        if not exists:
            raise StorageException("File not found in storage")

        metadata = material.metadata_ or {}
        metadata["upload_status"] = "complete"
        if checksum:
            metadata["checksum"] = checksum
        size = await self.storage.get_object_size(bucket, material.file_url)
        metadata["file_size"] = size
        material.metadata_ = metadata
        await self.db.flush()
        await self.activity.log(str(material.session_id), str(material.uploaded_by_id), "updated", "material", str(material.id))
        try:
            ingestion = MaterialIngestionService(self.db)
            await ingestion.ingest_material(material)
        except Exception as exc:
            logger.warning("Material ingestion failed", extra={"error": str(exc), "material_id": str(material.id)})
        return material

    async def cancel_upload(self, material_id: str | uuid.UUID) -> None:
        material_uuid = self._as_uuid(material_id)
        material = await self.db.get(Material, material_uuid)
        if not material:
            raise MaterialNotFound(material_id)

        if material.file_url:
            bucket = self.storage.bucket_for_material(material.material_type)
            await self.storage.delete_object(bucket, material.file_url)
        await self.activity.log(str(material.session_id), str(material.uploaded_by_id), "deleted", "material", str(material.id))
        await self.db.delete(material)
