from __future__ import annotations

import logging
from typing import Iterable

from app.db.redis_client import get_redis

logger = logging.getLogger(__name__)


class SearchAnalyticsService:
    def __init__(self, redis=None) -> None:
        self._redis = redis or get_redis()
        self._query_key = "search:global:queries"
        self._entity_key = "search:global:entity_counts"

    async def record_query(self, query: str, entities: Iterable[str]) -> None:
        normalized = query.strip().lower()
        if not normalized:
            return
        try:
            pipe = self._redis.pipeline()
            pipe.zincrby(self._query_key, 1, normalized)
            for entity in entities:
                pipe.hincrby(self._entity_key, entity, 1)
            await pipe.execute()
        except Exception as exc:
            logger.warning("Failed to record search analytics", extra={"error": str(exc)})
