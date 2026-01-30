import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worker.tasks.cleanup_tasks import cleanup_orphaned_files, cleanup_soft_deleted_materials


@pytest.mark.asyncio
async def test_cleanup_orphaned_files():
    storage = MagicMock()
    storage.cleanup_orphaned_objects = AsyncMock(return_value=5)

    res = await cleanup_orphaned_files(storage, {'a', 'b'})
    assert res == {"deleted": 5}


@pytest.mark.asyncio
async def test_cleanup_soft_deleted_materials():
    db = AsyncMock()
    # Return two rows to delete
    class R:
        def fetchall(self):
            return [("id1", "bucket/key1"), ("id2", "bucket/key2")]
    db.execute = AsyncMock(return_value=R())

    storage = MagicMock()
    storage.delete_file = AsyncMock(return_value=True)

    vector = MagicMock()
    vector.delete_vector = AsyncMock(return_value=True)

    res = await cleanup_soft_deleted_materials(db, storage, vector, older_than_days=30)
    assert res["deleted"] == 2
