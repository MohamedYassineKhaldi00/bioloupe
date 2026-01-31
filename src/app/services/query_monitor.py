from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.utils.query_inspector import QueryInspector


class QueryMonitorService:
    def __init__(
        self,
        inspector: QueryInspector | None = None,
        settings=None,
    ) -> None:
        cfg = settings or get_settings()
        self._inspector = inspector or QueryInspector(cfg.slow_query_threshold_ms)

    async def explain(self, session: AsyncSession, sql: str) -> list[str]:
        return await self._inspector.explain(session, sql)

    def log_if_slow(self, sql: str, duration_ms: float, context: dict[str, object] | None = None) -> None:
        self._inspector.log_if_slow(sql, duration_ms, context)
