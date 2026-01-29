import os
import time
import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.db.init_db import init_db
from app.db.base import async_session_maker
from app.services.session_service import SessionService
from app.schemas.session_schemas import SessionCreate
from app.services.qdrant_service import QdrantService
from app.services.storage_service import StorageService

RUN_INTEGRATION = os.environ.get("RUN_INTEGRATION")


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Integration test")
@pytest.mark.asyncio
async def test_session_service_and_qdrant_and_minio():
    # Wait and init DB
    for _ in range(30):
        try:
            await init_db()
            break
        except Exception:
            time.sleep(2)
    else:
        pytest.skip("DB not ready")

    # Create user and team and run SessionService flows
    async with async_session_maker() as session:
        # create user
        from app.models import User, Team
        user = User(email=f"int-{uuid.uuid4()}@example.com", hashed_password="x", full_name="Tester", is_active=True, is_verified=True)
        session.add(user)
        await session.flush()
        team = Team(name="Integration Team", description="t", created_by_id=user.id)
        session.add(team)
        await session.flush()
        await session.commit()
        user_id = str(user.id)
        team_id = str(team.id)

    # create a session via service
    async with async_session_maker() as db:
        svc = SessionService(db)
        payload = SessionCreate(team_id=team_id, title="Int Session", description="desc")
        created = await svc.create_session(payload, user_id)
        sid = str(created.id)
        assert created.title == "Int Session"

        # add participant
        await svc.add_participant(sid, str(user.id), "admin")
        parts = await svc.list_participants(sid)
        assert any(str(p.user_id) == str(user.id) for p in parts)

        # archive and unarchive
        await svc.archive_session(sid, user_id)
        db_ses = await svc.get_session(sid)
        assert db_ses.is_archived
        await svc.unarchive_session(sid, user_id)
        db_ses = await svc.get_session(sid)
        assert not db_ses.is_archived

        # update
        class _Upd:
            title = "New Title"
            description = None
            topic_tags = None

        await svc.update_session(sid, _Upd(), user_id)
        db_ses = await svc.get_session(sid)
        assert db_ses.title == "New Title"

    # Qdrant: create collection, upsert and search
    qsvc = QdrantService()
    collection = f"test_coll_{int(time.time())}"
    from qdrant_client.http import models as rest

    await qsvc.create_collection(collection, vector_size=4, distance=rest.Distance.COSINE)

    points = [
        {"id": "p1", "vector": [0.1, 0.0, 0.0, 0.0], "payload": {"text": "hello"}},
        {"id": "p2", "vector": [0.9, 0.0, 0.0, 0.0], "payload": {"text": "world"}},
    ]
    await qsvc.upsert_vectors(collection, points)

    res = await qsvc.search_vectors(collection, [0.95, 0.0, 0.0, 0.0], limit=1)
    assert res and res[0].id in {"p2", "p1"}

    await qsvc.delete_points(collection, ["p1", "p2"])
    await qsvc.delete_collection(collection)

    # MinIO multipart end-to-end
    storage = StorageService()
    await storage.ensure_buckets()
    bucket = storage.bucket_for_material(0)  # MaterialType.paper == 0
    key = storage.build_object_key(team_id, sid, "mat-int", "big.txt")

    # initiate multipart
    upload_id = await storage.initiate_multipart_upload(bucket, key, "text/plain")
    # upload one part
    async with storage.client() as client:
        resp = await client.upload_part(Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=1, Body=b"a" * 5)
        etag = resp.get("ETag")

    file_url = await storage.complete_multipart_upload(bucket, key, upload_id, parts=[{"PartNumber": 1, "ETag": etag}])
    assert file_url.startswith("s3://")

    exists = await storage.file_exists(bucket, key)
    assert exists

    await storage.delete_object(bucket, key)
    assert not await storage.file_exists(bucket, key)
