import os
import asyncio
import time

import pytest
from app.db.init_db import init_db
from app.db.base import async_session_maker
from sqlalchemy import select
from app.models import Team
from app.services.storage_service import StorageService
from app.services.qdrant_service import QdrantService

RUN_INTEGRATION = os.environ.get("RUN_INTEGRATION")


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Run with RUN_INTEGRATION=1 to execute integration tests")
@pytest.mark.asyncio
async def test_full_stack_minio_postgres_qdrant():
    # Wait for services to be up (simple retry)
    for i in range(30):
        try:
            # Attempt to init DB (will verify connection)
            await init_db()
            break
        except Exception:
            time.sleep(2)
    else:
        pytest.skip("Services did not become ready in time")

    # Verify we can query the DB
    async with async_session_maker() as session:
        result = await session.execute(select(Team).limit(1))
        _ = result.all()  # just ensure query runs

    # StorageService end-to-end test against MinIO
    storage = StorageService()
    await storage.ensure_buckets()
    bucket = storage.bucket_for_material(None if False else 0)  # MaterialType.paper is enum 0
    key = storage.build_object_key("team-test", "session-test", "mat-test", "file.txt")

    # put object
    async with storage.client() as client:
        await client.put_object(Bucket=bucket, Key=key, Body=b"hello")

    exists = await storage.file_exists(bucket, key)
    assert exists
    size = await storage.get_object_size(bucket, key)
    assert size == 5
    await storage.delete_object(bucket, key)

    # Qdrant health and create/delete collection
    qsvc = QdrantService()
    healthy = await qsvc.health_check()
    assert healthy is True

    collection_name = f"test_collection_{int(time.time())}"
    await qsvc.create_collection(collection_name, vector_size=8, distance=getattr(__import__('qdrant_client.http.models', fromlist=['Distance']), 'Distance').__dict__.get('Cosine', 0))
    info = await qsvc.collection_info(collection_name)
    assert info is not None
    await qsvc.delete_collection(collection_name)
