import os
import asyncio
import pytest

from app.services.storage_service import StorageService
from app.models.material import MaterialType

MINIO_FLAG = os.environ.get("RUN_MINIO_TESTS")


@pytest.mark.skipif(not MINIO_FLAG, reason="Requires RUN_MINIO_TESTS=1 and MinIO running")
@pytest.mark.asyncio
async def test_storage_end_to_end_minio():
    # This test requires a running MinIO instance with credentials set in env vars (see .env.example)
    storage = StorageService()

    # Ensure buckets exist
    await storage.ensure_buckets()

    bucket = storage.bucket_for_material(MaterialType.paper)
    key = storage.build_object_key("team-x", "session-x", "mat-x", "file.txt")

    # Upload a small object using the aioboto3 client exposed by StorageService
    async with storage.client() as client:
        await client.put_object(Bucket=bucket, Key=key, Body=b"hello")

    exists = await storage.file_exists(bucket, key)
    assert exists is True

    size = await storage.get_object_size(bucket, key)
    assert size == 5

    # cleanup
    await storage.delete_object(bucket, key)
    assert not await storage.file_exists(bucket, key)
