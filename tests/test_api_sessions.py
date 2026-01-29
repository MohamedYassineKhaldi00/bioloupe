from types import SimpleNamespace

from app.api.dependencies.auth import get_current_active_user
from app.db.base import get_db


def make_fake_session_service():
    class FakeSession:
        def __init__(self, id, title, team_id):
            from datetime import datetime
            self.id = id
            self.title = title
            self.team_id = team_id
            self.description = None
            self.topic_tags = []
            self.created_by_id = "user-1"
            self.is_archived = False
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.deleted_at = None

    class FakeParticipant(SimpleNamespace):
        pass

    class FakeSessionService:
        def __init__(self, db):
            self.db = db

        async def create_session(self, payload, user_id):
            from datetime import datetime
            return FakeSession("session-1", payload.title, payload.team_id)

        async def list_sessions_paginated(self, session_ids, team_id, include_archived, tags, skip, limit):
            from datetime import datetime
            return ([{"id": "session-1", "team_id": team_id or "team-1", "title": "S1", "description": None, "topic_tags": [], "is_archived": False, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}], 1)

        async def search_sessions(self, q, team_id, include_archived):
            return [FakeSession("session-1", "SearchResult", team_id)]

        async def add_participant(self, session_id, user_id, permission):
            from datetime import datetime
            return FakeParticipant(id="part-1", session_id=session_id, user_id=user_id, permission=permission, joined_at=datetime.utcnow())

        async def list_participants(self, session_id):
            from datetime import datetime
            return [FakeParticipant(id="part-1", session_id=session_id, user_id="user-2", permission="admin", joined_at=datetime.utcnow())]

        async def session_stats(self, session_id):
            return {"material_counts": {"paper": 3}, "participant_count": 2, "activity_count": 0}

    return FakeSessionService


async def _get_current_user():
    return SimpleNamespace(id="user-1", email="test@example.com")


async def _get_db_with_participation(session_ids=("session-1",)):
    class FakeDB:
        async def execute(self, stmt):
            class Result:
                def all(self_inner):
                    return [(sid,) for sid in session_ids]

                def scalar_one_or_none(self_inner):
                    return None

                def scalar_one(self_inner):
                    return len(session_ids)

                def scalars(self_inner):
                    class _Scalars:
                        def all(self2):
                            return []

                    return _Scalars()

            return Result()

        async def get(self, model, id):
            if id == "session-1":
                return SimpleNamespace(id="session-1", deleted_at=None)
            return None

    async def _inner():
        yield FakeDB()

    return _inner


def test_create_session_success(client, monkeypatch):
    # Patch permission check and session service
    async def _no_team_perm(*a, **k):
        return None

    monkeypatch.setattr("app.api.v1.endpoints.sessions.require_team_permission", _no_team_perm)
    Fake = make_fake_session_service()
    monkeypatch.setattr("app.api.v1.endpoints.sessions.SessionService", Fake)
    monkeypatch.setattr("app.api.v1.endpoints.sessions.get_current_active_user", _get_current_user)

    resp = client.post("/api/v1/sessions", json={"title": "New Session", "team_id": "team-1", "description": "x"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "session-1"
    assert data["title"] == "New Session"


def test_list_sessions_paginated(client, monkeypatch):
    # Provide DB that returns participation in session-1
    async def _get_db_override():
        class FakeDB:
            async def execute(self, stmt):
                class Result:
                    def all(self_inner):
                        return [("session-1",)]

                return Result()

        yield FakeDB()

    # Override the app dependency to ensure the route uses our DB stub
    client.app.dependency_overrides[get_db] = _get_db_override
    Fake = make_fake_session_service()
    monkeypatch.setattr("app.api.v1.endpoints.sessions.SessionService", Fake)

    resp = client.get("/api/v1/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "S1"


def test_add_and_list_participants(client, monkeypatch):
    # Patch permission check and service
    async def fake_require_session_permission(session_id, perms, current_user, db):
        return SimpleNamespace(id=session_id)

    monkeypatch.setattr("app.api.v1.endpoints.sessions.require_session_permission", fake_require_session_permission)
    # Also patch the closure factory used by endpoints to obtain permission dependency
    monkeypatch.setattr("app.api.v1.endpoints.sessions.session_permission_required", lambda perms: (lambda *a, **k: SimpleNamespace(id="session-1")))
    Fake = make_fake_session_service()
    monkeypatch.setattr("app.api.v1.endpoints.sessions.SessionService", Fake)

    resp = client.post("/api/v1/sessions/session-1/participants", json={"user_id": "user-2", "permission": "admin"})
    assert resp.status_code == 200
    part = resp.json()
    assert part["user_id"] == "user-2"
    assert "joined_at" in part

    # ensure get_db has a get() implementation for the permission dependency
    async def _get_db_override_for_perm():
        class FakeDB:
            async def get(self, model, id):
                if id == "session-1":
                    return SimpleNamespace(id="session-1", deleted_at=None)
                return None

            async def execute(self, stmt):
                class Result:
                    def scalar_one_or_none(self_inner):
                        return SimpleNamespace(permission="read")

                return Result()

        yield FakeDB()

    client.app.dependency_overrides[get_db] = _get_db_override_for_perm

    resp = client.get("/api/v1/sessions/session-1/participants")
    assert resp.status_code == 200
    parts = resp.json()
    assert isinstance(parts, list)
    assert parts and parts[0]["user_id"] == "user-2"


def test_get_permissions_no_permission(client, monkeypatch):
    # DB returns no permission
    async def _get_db_override():
        class FakeDB:
            async def execute(self, stmt):
                class Result:
                    def scalar_one_or_none(self_inner):
                        return None

                return Result()

        yield FakeDB()

    # Ensure the route uses our DB stub for this test
    client.app.dependency_overrides[get_db] = _get_db_override
    resp = client.get("/api/v1/sessions/session-1/permissions")
    assert resp.status_code == 403


def test_session_stats(client, monkeypatch):
    async def fake_require_session_permission(session_id, perms, current_user, db):
        return SimpleNamespace(id=session_id)

    monkeypatch.setattr("app.api.v1.endpoints.sessions.require_session_permission", fake_require_session_permission)
    Fake = make_fake_session_service()
    monkeypatch.setattr("app.api.v1.endpoints.sessions.SessionService", Fake)

    resp = client.get("/api/v1/sessions/session-1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["participant_count"] == 2
    assert data["material_counts"]["paper"] == 3
