from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from math import ceil
from datetime import datetime, timezone

import aioboto3

from app.core.config import get_settings
from app.core.exceptions import StorageException
from app.core.storage_config import STORAGE_BUCKETS, STORAGE_LIMITS
from app.models.material import MaterialType

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._session = aioboto3.Session()

    @property
    def _use_minio(self) -> bool:
        return self._settings.environment != "production" or not self._settings.aws_access_key_id

    def _endpoint_url(self) -> str | None:
        if self._use_minio:
            endpoint = self._settings.minio_endpoint
            if endpoint.startswith("http://") or endpoint.startswith("https://"):
                return endpoint
            return f"http://{endpoint}"
        return None

    def _bucket_name(self, base_name: str) -> str:
        if self._use_minio:
            return base_name
        prefix = self._settings.aws_s3_bucket_prefix
        return f"{prefix}-{base_name.split('-')[-1]}"

    def bucket_for_material(self, material_type: MaterialType) -> str:
        mapping = {
            MaterialType.paper: STORAGE_BUCKETS.papers,
            MaterialType.sequence: STORAGE_BUCKETS.sequences,
            MaterialType.image: STORAGE_BUCKETS.images,
            MaterialType.experiment: STORAGE_BUCKETS.experimental_data,
            MaterialType.note: STORAGE_BUCKETS.papers,
        }
        return self._bucket_name(mapping[material_type])

    @asynccontextmanager
    async def client(self):
        try:
            async with self._session.client(
                "s3",
                endpoint_url=self._endpoint_url(),
                region_name=self._settings.aws_region,
                aws_access_key_id=self._settings.aws_access_key_id or self._settings.minio_access_key,
                aws_secret_access_key=self._settings.aws_secret_access_key or self._settings.minio_secret_key,
            ) as client:
                yield client
        except Exception as exc:
            raise StorageException(f"Storage client error: {exc}") from exc

    async def ensure_buckets(self) -> None:
        async with self.client() as client:
            for bucket in [
                STORAGE_BUCKETS.papers,
                STORAGE_BUCKETS.sequences,
                STORAGE_BUCKETS.images,
                STORAGE_BUCKETS.experimental_data,
                STORAGE_BUCKETS.temp,
            ]:
                name = self._bucket_name(bucket)
                try:
                    await client.head_bucket(Bucket=name)
                except Exception:
                    await client.create_bucket(Bucket=name)

    def build_object_key(self, team_id: str, session_id: str, material_id: str, filename: str) -> str:
        return f"{team_id}/{session_id}/{material_id}/{filename}"

    async def generate_presigned_upload(self, bucket: str, key: str, content_type: str) -> str:
        async with self.client() as client:
            return client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=STORAGE_LIMITS.presign_expiry_seconds,
            )

    async def generate_presigned_download(self, bucket: str, key: str) -> str:
        async with self.client() as client:
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=STORAGE_LIMITS.presign_expiry_seconds,
            )

    async def initiate_multipart_upload(self, bucket: str, key: str, content_type: str) -> str:
        async with self.client() as client:
            response = await client.create_multipart_upload(
                Bucket=bucket,
                Key=key,
                ContentType=content_type,
            )
            return response["UploadId"]

    async def generate_presigned_part_urls(
        self, bucket: str, key: str, upload_id: str, file_size: int
    ) -> list[tuple[int, str]]:
        part_size = STORAGE_LIMITS.multipart_part_size_bytes
        total_parts = max(1, ceil(file_size / part_size))
        urls: list[tuple[int, str]] = []

        async with self.client() as client:
            for part_number in range(1, total_parts + 1):
                url = client.generate_presigned_url(
                    "upload_part",
                    Params={
                        "Bucket": bucket,
                        "Key": key,
                        "UploadId": upload_id,
                        "PartNumber": part_number,
                    },
                    ExpiresIn=STORAGE_LIMITS.presign_expiry_seconds,
                )
                urls.append((part_number, url))

        return urls

    async def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, str | int]],
    ) -> str:
        async with self.client() as client:
            await client.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            return f"s3://{bucket}/{key}"

    async def abort_multipart_upload(self, bucket: str, key: str, upload_id: str) -> None:
        async with self.client() as client:
            await client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)

    async def delete_object(self, bucket: str, key: str) -> None:
        async with self.client() as client:
            await client.delete_object(Bucket=bucket, Key=key)

    async def cleanup_orphaned_objects(
        self,
        valid_keys: set[str],
        cutoff_seconds: int = 7 * 24 * 60 * 60,
    ) -> int:
        removed = 0
        async with self.client() as client:
            for bucket in [
                STORAGE_BUCKETS.papers,
                STORAGE_BUCKETS.sequences,
                STORAGE_BUCKETS.images,
                STORAGE_BUCKETS.experimental_data,
                STORAGE_BUCKETS.temp,
            ]:
                name = self._bucket_name(bucket)
                paginator = client.get_paginator("list_objects_v2")
                async for page in paginator.paginate(Bucket=name):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        if key in valid_keys:
                            continue
                        age_seconds = (datetime.now(timezone.utc) - obj["LastModified"]).total_seconds()
                        if age_seconds >= cutoff_seconds:
                            await client.delete_object(Bucket=name, Key=key)
                            removed += 1
        return removed

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(data)
        return digest.hexdigest()

    async def presign_upload_or_multipart(
        self, bucket: str, key: str, content_type: str, file_size: int
    ) -> tuple[str | None, str | None, list[tuple[int, str]] | None]:
        if file_size >= STORAGE_LIMITS.multipart_threshold_bytes:
            upload_id = await self.initiate_multipart_upload(bucket, key, content_type)
            part_urls = await self.generate_presigned_part_urls(bucket, key, upload_id, file_size)
            return None, upload_id, part_urls

        url = await self.generate_presigned_upload(bucket, key, content_type)
        return url, None, None
