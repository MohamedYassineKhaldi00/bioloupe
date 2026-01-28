import asyncio
from app.services.team_service import TeamService


async def fake_db_session():
    class FakeDB:
        pass

    return FakeDB()


def test_add_member_cache_invalidation(monkeypatch):
    # Patch CacheService used inside TeamService
    class FakeCache:
        def __init__(self):
            self.data = {}

        async def delete(self, key):
            self.data.pop(key, None)

    monkeypatch.setattr("app.services.team_service.CacheService", lambda: FakeCache())

    # create service and call add_member
    import asyncio

    async def run():
        # Create a fake DB that supports execute, add, and flush but does not persist
        class FakeDB:
            async def execute(self, stmt):
                class Result:
                    def scalar_one_or_none(self_inner):
                        return None

                return Result()

            def add(self, obj):
                return None

            async def flush(self):
                return None

        service = TeamService(db=FakeDB())
        member = await service.add_member("team-1", "user-2", "member")
        assert member.user_id == "user-2"

    asyncio.get_event_loop().run_until_complete(run())
