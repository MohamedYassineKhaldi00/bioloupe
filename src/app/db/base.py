from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import AsyncIterator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


settings = get_settings()
import os

# Engines and session makers used by the runtime.
engine = None
async_session_maker = None
replica_engine = None
replica_session_maker = None

# During tests we prefer not to initialize a real DB engine (missing drivers in test env).
# Honor TESTING=1 to skip expensive engine creation and provide a simple fake session.
if os.environ.get("TESTING"):
    class _DummySession:
        async def commit(self):
            pass

        async def rollback(self):
            pass

        async def close(self):
            pass

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        yield _DummySession()

    async def get_replica_db() -> AsyncGenerator[AsyncSession, None]:
        yield _DummySession()
else:
    # Check if using SQLite and adjust engine parameters accordingly
    if settings.database_url.startswith("sqlite"):
        engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
        )
    else:
        engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )

    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    if settings.read_replica_url:
        if settings.read_replica_url.startswith("sqlite"):
            replica_engine = create_async_engine(
                settings.read_replica_url,
                pool_pre_ping=True,
            )
        else:
            replica_engine = create_async_engine(
                settings.read_replica_url,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,
            )
        replica_session_maker = async_sessionmaker(replica_engine, expire_on_commit=False)


    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


    async def get_replica_db() -> AsyncGenerator[AsyncSession, None]:
        if replica_session_maker is None:
            async for session in get_db():
                yield session
            return

        async with replica_session_maker() as session:
            yield session


async def verify_connection(retries: int = 5, base_delay: float = 0.5) -> None:
    if engine is None:
        logger.info("Skipping DB connection verification in TESTING mode")
        return

    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            if attempt == retries:
                logger.error("Database connection failed", extra={"attempt": attempt})
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("Database connection retry", extra={"attempt": attempt, "delay": delay})
            await asyncio.sleep(delay)
