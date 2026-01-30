from __future__ import annotations

import logging
from datetime import datetime, timedelta
from app.worker.celery_app import get_task_decorator

logger = logging.getLogger(__name__)
_task = get_task_decorator()


@_task()
async def cleanup_orphaned_files(storage_service, valid_keys: set[str], cutoff_days: int = 7):
    try:
        deleted = await storage_service.cleanup_orphaned_objects(valid_keys=valid_keys, cutoff_seconds=cutoff_days * 24 * 3600)
        return {"deleted": deleted}
    except Exception as e:
        logger.exception("cleanup_orphaned_files failed: %s", e)
        raise


@_task()
async def cleanup_soft_deleted_materials(db, storage_service, vector_service, older_than_days: int = 30):
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)

    try:
        # Example: delete materials with deleted_at < cutoff
        result = await db.execute("SELECT id, file_url FROM materials WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff", {"cutoff": cutoff})
        rows = result.fetchall()

        deleted = 0
        for row in rows:
            mid = row[0]
            file_url = row[1]
            # delete from qdrant
            try:
                await vector_service.delete_vector("bioloupe_publications", str(mid))
            except Exception:
                logger.exception("Failed to delete vector for %s", mid)
            # delete file if exists
            if file_url:
                try:
                    await storage_service.delete_file(bucket=file_url.split('/', 1)[0], key=file_url)
                except Exception:
                    logger.exception("Failed to delete file for %s", mid)
            deleted += 1

        return {"deleted": deleted}
    except Exception as e:
        logger.exception("cleanup_soft_deleted_materials failed: %s", e)
        raise