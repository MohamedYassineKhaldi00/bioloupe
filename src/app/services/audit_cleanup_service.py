from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...app.core.config import get_settings
from ...app.db.base import async_session_maker
from ...app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def cleanup_old_audit_logs(db: AsyncSession) -> int:
    settings = get_settings()
    retention_days = settings.audit_log_retention_days

    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    delete_stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)

    result = await db.execute(delete_stmt)
    deleted_count = result.rowcount

    await db.commit()

    logger.info(
        f"Deleted {deleted_count} audit logs older than {retention_days} days"
    )

    return deleted_count


async def get_audit_log_statistics(db: AsyncSession) -> dict:
    from sqlalchemy import func

    total_query = select(func.count()).select_from(AuditLog)
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    oldest_query = select(func.min(AuditLog.timestamp))
    oldest_result = await db.execute(oldest_query)
    oldest = oldest_result.scalar()

    newest_query = select(func.max(AuditLog.timestamp))
    newest_result = await db.execute(newest_query)
    newest = newest_result.scalar()

    return {
        "total_logs": total,
        "oldest_log": oldest.isoformat() if oldest else None,
        "newest_log": newest.isoformat() if newest else None,
    }


async def run_cleanup_task() -> None:
    try:
        async with async_session_maker() as session:
            stats_before = await get_audit_log_statistics(session)
            logger.info(f"Audit log statistics before cleanup: {stats_before}")

            deleted_count = await cleanup_old_audit_logs(session)

            stats_after = await get_audit_log_statistics(session)
            logger.info(f"Audit log statistics after cleanup: {stats_after}")

    except Exception as exc:
        logger.error(f"Audit log cleanup failed: {exc}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_cleanup_task())
