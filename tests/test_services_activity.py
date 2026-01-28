import asyncio
from types import SimpleNamespace

from app.services.activity_service import ActivityService


def test_activity_log_adds_entry_and_flush_called(monkeypatch):
    flushed = {"called": False}

    class FakeDB:
        def __init__(self):
            self.added = []

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            flushed["called"] = True

    async def run():
        db = FakeDB()
        svc = ActivityService(db=db)
        entry = await svc.log("session-1", "user-1", "create", "material", "mat-1", {"x": 1})
        assert entry.session_id == "session-1"
        assert entry.entity_id == "mat-1"
        assert flushed["called"]

    asyncio.get_event_loop().run_until_complete(run())
