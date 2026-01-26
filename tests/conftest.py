from __future__ import annotations

import asyncio
import os
from typing import Generator

import pytest

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://bioloupe:bioloupe@localhost:5432/bioloupe_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"
os.environ["MINIO_SECURE"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-not-for-production"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["JWT_REFRESH_TOKEN_EXPIRE_DAYS"] = "7"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
