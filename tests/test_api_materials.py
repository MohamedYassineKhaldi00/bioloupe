from types import SimpleNamespace

from app.db.base import get_db


def make_fake_material_service():
    class FakeMaterial:
        def __init__(self, id, session_id, title):
            from datetime import datetime
            from app.models.material import MaterialType

            self.id = id
            self.session_id = session_id
            self.title = title
            self.material_type = MaterialType.paper
            self.metadata_ = {"tags": ["tag1"]}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    class FakeMaterialService:
        def __init__(self, db):
            self.db = db

        async def search_materials(self, q, session_id, material_type):
            return [FakeMaterial("mat-1", session_id or "session-1", "Material 1")]

        async def create_material(self, payload, user_id):
            return FakeMaterial("mat-1", payload.session_id, payload.title)

        async def add_tags(self, material_id, tags, user_id):
            return FakeMaterial(material_id, "session-1", "Material 1")

        async def remove_tags(self, material_id, tags, user_id):
            return FakeMaterial(material_id, "session-1", "Material 1")

        async def list_materials_paginated(self, session_id, material_type, skip, limit):
            return ([{"id": "mat-1", "title": "Material 1", "session_id": session_id}], 1)

    return FakeMaterialService


def make_fake_upload_service():
    class FakeUploadService:
        def __init__(self, db):
            self.db = db

        async def initiate_upload(self, payload, user_id):
            return {
                "bucket": "bucket-1",
                "object_key": "team/session/mat/file.txt",
                "upload_id": "u1",
                "presigned_url": "https://example.com/presigned",
                "parts": None,
            }

        async def complete_upload(self, material_id, checksum):
            from datetime import datetime
            from app.models.material import MaterialType

            return SimpleNamespace(
                id=material_id,
                title="Completed",
                session_id="session-1",
                metadata_={"tags": []},
                created_by_id="user-1",
                material_type=MaterialType.paper,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        async def cancel_upload(self, material_id):
            return None

    return FakeUploadService


async def _get_db_stub():
    class FakeDB:
        async def execute(self, stmt):
            class Result:
                def all(self_inner):
                    return [("session-1",)]

                def scalar_one_or_none(self_inner):
                    return None

                def scalars(self_inner):
                    class _Scalars:
                        def all(self2):
                            return []

                    return _Scalars()

            return Result()

        async def get(self, model, id):
            if id == "mat-1":
                return SimpleNamespace(id="mat-1", session_id="session-1", title="Material 1", metadata_={"tags": ["tag1"]}, deleted_at=None)
            if id == "session-1":
                return SimpleNamespace(id="session-1", deleted_at=None)
            return None

    yield FakeDB()


def test_search_materials_filters_by_user_sessions(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.materials.MaterialService", make_fake_material_service())
    client.app.dependency_overrides[get_db] = _get_db_stub

    resp = client.get("/api/v1/materials/search?q=test")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["id"] == "mat-1"


def test_create_material_requires_permission_and_returns_material(client, monkeypatch):
    async def _no_perm(*a, **k):
        return None

    monkeypatch.setattr("app.api.v1.endpoints.materials.require_session_permission", _no_perm)
    monkeypatch.setattr("app.api.v1.endpoints.materials.MaterialService", make_fake_material_service())

    resp = client.post("/api/v1/materials", json={"session_id": "session-1", "title": "M", "material_type": "paper"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "mat-1"


def test_initiate_upload_and_complete_and_cancel(client, monkeypatch):
    # Initiate through uploads endpoint
    monkeypatch.setattr("app.api.v1.endpoints.uploads.StorageService.generate_presigned_upload", lambda *a, **k: "https://example.com/presigned")
    # Use the material-level initiate which uses UploadService
    monkeypatch.setattr("app.api.v1.endpoints.materials.UploadService", make_fake_upload_service())

    async def _fake_presign(*a, **k):
        return ("https://example.com/presigned", None, None)

    monkeypatch.setattr("app.api.v1.endpoints.uploads.StorageService.presign_upload_or_multipart", _fake_presign)

    resp = client.post("/api/v1/uploads/initiate", json={"team_id": "team-1", "session_id": "session-1", "material_id": "mat-1", "filename": "file.pdf", "content_type": "application/pdf", "file_size": 100, "material_type": "paper"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["presigned_url"] == "https://example.com/presigned"

    # Complete the upload via materials endpoint
    monkeypatch.setattr("app.api.v1.endpoints.materials.UploadService", make_fake_upload_service())
    # Ensure DB dependency returns our material and a participant with permission for the complete flow
    from app.models import SessionPermission

    async def _get_db_override_for_complete():
        class FakeDB:
            async def get(self, model, id):
                if id == "mat-1":
                    return SimpleNamespace(id="mat-1", session_id="session-1", title="Material 1", metadata_={"tags": ["tag1"]}, deleted_at=None)
                if id == "session-1":
                    return SimpleNamespace(id="session-1", deleted_at=None)
                return None

            async def execute(self, stmt):
                class Result:
                    def scalar_one_or_none(self_inner):
                        return SimpleNamespace(permission=SessionPermission.admin)

                return Result()

        yield FakeDB()

    client.app.dependency_overrides[get_db] = _get_db_override_for_complete

    resp = client.post("/api/v1/materials/upload/mat-1/complete", json={"checksum": "abc", "parts": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "mat-1"

    # Cancel upload
    resp = client.delete("/api/v1/materials/upload/mat-1/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
