from __future__ import annotations

import sys
import os
import asyncio
from typing import Generator
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Minimal environment for tests to avoid Pydantic Settings validation errors at import time
# Defaults chosen to avoid requiring external services during unit tests; CI can override these.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MINIO_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECURE", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-not-for-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")

# If aiosqlite is not installed in the test environment, provide a minimal dummy module
aiosqlite_mod = sys.modules.setdefault("aiosqlite", types.ModuleType("aiosqlite"))
# provide a few attributes SQLAlchemy's dialect expects during import
setattr(aiosqlite_mod, "DatabaseError", Exception)
setattr(aiosqlite_mod, "OperationalError", Exception)
setattr(aiosqlite_mod, "connect", lambda *a, **k: None)
setattr(aiosqlite_mod, "Cursor", object)
setattr(aiosqlite_mod, "Connection", object)
setattr(aiosqlite_mod, "Row", tuple)
setattr(aiosqlite_mod, "PARSE_DECLTYPES", None)
setattr(aiosqlite_mod, "Error", Exception)

# Provide a minimal fake qdrant_client.http.models module so imports succeed in tests
_qdrant = sys.modules.setdefault("qdrant_client", types.ModuleType("qdrant_client"))
# minimal AsyncQdrantClient placeholder
setattr(_qdrant, "AsyncQdrantClient", type("AsyncQdrantClient", (), {}))
_qdrant_http = sys.modules.setdefault("qdrant_client.http", types.ModuleType("qdrant_client.http"))
_qdrant_models = types.ModuleType("qdrant_client.http.models")
for name in ("PointStruct", "UpdateResult", "ScoredPoint", "Filter", "PointIdsList", "CollectionInfo", "Distance", "VectorParams"):
    setattr(_qdrant_models, name, type(name, (), {}))
sys.modules["qdrant_client.http.models"] = _qdrant_models

# Provide a minimal aioboto3 shim so storage_service can import without the package
_aioboto3 = sys.modules.setdefault("aioboto3", types.ModuleType("aioboto3"))

class _DummyClient:
    def generate_presigned_url(self, *a, **k):
        return "https://example.com/presigned"

    async def head_object(self, *a, **k):
        return {"ContentLength": 123}

    async def delete_object(self, *a, **k):
        return None

    async def create_multipart_upload(self, *a, **k):
        return {"UploadId": "upload-1"}

    async def complete_multipart_upload(self, *a, **k):
        return None

    async def abort_multipart_upload(self, *a, **k):
        return None

    def get_paginator(self, name):
        class Paginator:
            async def paginate(self, *a, **k):
                yield {"Contents": []}

        return Paginator()

class _DummySession:
    def client(self, *a, **k):
        class CM:
            async def __aenter__(self):
                return _DummyClient()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return CM()

setattr(_aioboto3, "Session", _DummySession)


import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app():
    """Create the FastAPI app with basic dependency overrides for tests."""
    from app.main import create_app
    from app.api.dependencies.auth import get_current_active_user
    from app.db.base import get_db

    app = create_app()

    # simple test user object used by auth dependency override
    test_user = SimpleNamespace(id="user-1", email="test@example.com")

    async def _get_current_user():
        return test_user

    async def _get_db():
        # Provide a lightweight fake DB object for endpoints that expect a session.
        class _FakeDB:
            async def get(self, model, id):
                # return a simple team-like object for team-1
                if id == "team-1":
                    return SimpleNamespace(id="team-1", name="T1", description="desc")
                return None

            async def execute(self, stmt):
                # For permission checks return a result that has scalar_one_or_none()
                class _Result:
                    def scalar_one_or_none(self_inner):
                        # Import TeamRole to return an enum for role comparisons
                        from app.models import TeamRole

                        return SimpleNamespace(role=TeamRole.owner)

                return _Result()

        yield _FakeDB()

    # Override dependencies so tests don't require a running DB or auth flow
    app.dependency_overrides[get_current_active_user] = _get_current_user
    app.dependency_overrides[get_db] = _get_db

    return app


@pytest.fixture
def client(app):
    return TestClient(app)
