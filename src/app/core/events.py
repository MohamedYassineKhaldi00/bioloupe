from __future__ import annotations

import logging

from ..core.config import get_settings
from ..core.ml_config import get_ml_settings
from ..db.base import engine, verify_connection
from ..db.init_db import init_db
from ..db.init_qdrant import init_qdrant
from ..db.redis_client import close_redis
from ..services.embedding import get_model_loader
from ..services.storage_service import StorageService
from ..websocket import server as ws_server

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

    # Warm up ML models if enabled
    ml_settings = get_ml_settings()
    if ml_settings.ml_model_warmup:
        try:
            model_loader = get_model_loader()
            await model_loader.warmup_models(["specter2", "esm2", "clip"])
            logger.info("ML models warmed up")
        except Exception as e:
            logger.warning(f"ML model warmup failed: {e}")

    # Start WebSocket background tasks
    await ws_server.start_background_tasks()
    logger.info("WebSocket background tasks started")

    logger.info("Application startup complete")


async def shutdown_event() -> None:
    logger.info("Starting graceful shutdown")

    # Stop WebSocket background tasks
    await ws_server.stop_background_tasks()
    logger.info("WebSocket background tasks stopped")

    # Unload ML models
    try:
        model_loader = get_model_loader()
        for model_name in model_loader.get_loaded_models():
            await model_loader.unload_model(model_name)
        logger.info("ML models unloaded")
    except Exception as e:
        logger.warning(f"ML model cleanup failed: {e}")

    await close_redis()
    logger.info("Redis connection closed")

    await engine.dispose()
    logger.info("Database connection pool disposed")

    logger.info("Application shutdown complete")
