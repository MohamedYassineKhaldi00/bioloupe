import pytest
import asyncio
from unittest.mock import AsyncMock
from app.services.task_service import TaskService


class FakeRedis:
    def __init__(self):
        self._store = {}

    async def set(self, key, val):
        self._store[key] = val

    async def get(self, key):
        return self._store.get(key)


@pytest.mark.asyncio
async def test_set_and_get_progress(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr('app.services.task_service.get_redis', lambda: fake)
    # Also patch the internal _redis via constructor
    service = TaskService()
    # override internal to our fake directly
    service._redis = fake

    await service.set_progress('t1', 1, 10, 'processing')
    prog = await service.get_progress('t1')
    assert prog.task_id == 't1'
    assert prog.current == 1
    assert prog.total == 10


@pytest.mark.asyncio
async def test_set_and_get_result(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr('app.services.task_service.get_redis', lambda: fake)
    service = TaskService()
    service._redis = fake

    await service.set_result('t2', {'ok': True})
    res = await service.get_result('t2')
    assert res.task_id == 't2'
    assert res.result == {'ok': True}
