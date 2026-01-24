from __future__ import annotations

import logging

from ..core.config import get_settings
from ..db.base import engine, verify_connection
from ..db.init_db import init_db
from ..db.init_qdrant import init_qdrant
from ..db.redis_client import close_redis
from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)


async def startup_event() -> None:
    settings = get_settings()
    logger.info("Starting BioLoupe backend", extra={"environment": settings.environment})
    
    await verify_connection()
    logger.info("Database connection verified")
    
    await init_db()
    logger.info("Database initialized")
    
    await init_qdrant()
    logger.info("Qdrant collections initialized")
    
    storage = StorageService()
    await storage.ensure_buckets()
    logger.info("Storage buckets ensured")
    
    logger.info("Application startup complete")


async def shutdown_event() -> None:
    logger.info("Starting graceful shutdown")
    
    await close_redis()
    logger.info("Redis connection closed")
    
    await engine.dispose()
    logger.info("Database connection pool disposed")
    
    logger.info("Application shutdown complete")
