from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class QueryInspector:
    def __init__(self, slow_query_threshold_ms: int) -> None:
        self._threshold = slow_query_threshold_ms

    async def explain(self, session: AsyncSession, sql: str) -> list[str]:
        stmt = text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]

    def log_if_slow(self, sql: str, duration_ms: float, context: dict[str, Any] | None = None) -> None:
        if duration_ms < self._threshold:
            return
        payload = {
            "sql": sql,
            "duration_ms": duration_ms,
        }
        if context:
            payload.update(context)
        logger.warning("Slow query detected", extra=payload)
