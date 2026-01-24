from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class QdrantClientWrapper:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30.0,
            prefer_grpc=False,
        )

    @property
    def client(self) -> AsyncQdrantClient:
        return self._client

    async def close(self) -> None:
        await self._client.close()

    async def with_retry(
        self,
        operation: Callable[..., Awaitable[T]],
        *args,
        retries: int = 5,
        base_delay: float = 0.5,
        **kwargs,
    ) -> T:
        for attempt in range(1, retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as exc:
                if attempt == retries:
                    logger.error("Qdrant operation failed", extra={"attempt": attempt})
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Qdrant retry",
                    extra={"attempt": attempt, "delay": delay, "error": str(exc)},
                )
                await asyncio.sleep(delay)
        raise RuntimeError("Retry loop exited unexpectedly")


_qdrant_wrapper: QdrantClientWrapper | None = None


def get_qdrant_client() -> QdrantClientWrapper:
    global _qdrant_wrapper
    if _qdrant_wrapper is None:
        _qdrant_wrapper = QdrantClientWrapper()
    return _qdrant_wrapper
