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

    # Skip Qdrant initialization for local development
    try:
        if not getattr(settings, 'disable_vector_search', False):
            await init_qdrant()
            logger.info("Qdrant collections initialized")
        else:
            logger.info("Qdrant initialization skipped (disabled for local development)")
    except Exception as e:
        logger.warning(f"Qdrant initialization failed: {e}, continuing without vector search")

    # Skip MinIO initialization for local development
    try:
        if not getattr(settings, 'disable_minio', False):
            storage = StorageService()
            await storage.ensure_buckets()
            logger.info("Storage buckets ensured")
        else:
            logger.info("MinIO initialization skipped (disabled for local development)")
    except Exception as e:
        logger.warning(f"MinIO initialization failed: {e}, continuing without storage")

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

    # Create demo account & workspace (development convenience)
    try:
        if getattr(settings, "demo_enabled", False):
            from sqlalchemy import select
            from uuid import uuid4
            from app.core.security import hash_password
            from app.models.user import User
            from app.models.team import Team
            from app.models.session import Session
            from app.services.team_service import TeamService
            from app.services.session_service import SessionService
            from app.db.base import async_session_maker

            async with async_session_maker() as db:
                # Demo user
                result = await db.execute(select(User).where(User.email == settings.demo_email))
                demo_user = result.scalar_one_or_none()
                if not demo_user:
                    demo_user = User(
                        id=uuid4(),
                        email=settings.demo_email,
                        hashed_password=hash_password(settings.demo_password),
                        full_name=settings.demo_full_name,
                        is_active=True,
                        is_verified=True,
                    )
                    db.add(demo_user)
                    await db.flush()
                    logger.info("Demo user created", extra={"email": settings.demo_email})
                else:
                    demo_user.hashed_password = hash_password(settings.demo_password)
                    demo_user.full_name = settings.demo_full_name
                    demo_user.is_active = True
                    demo_user.is_verified = True
                    await db.flush()
                    logger.info("Demo user updated", extra={"email": settings.demo_email})

                # Demo team
                team_result = await db.execute(select(Team).where(Team.name == settings.demo_team_name))
                demo_team = team_result.scalar_one_or_none()
                if not demo_team:
                    team_service = TeamService(db)
                    demo_team = await team_service.create_team(settings.demo_team_name, "Demo team created by startup seeder", str(demo_user.id))
                    logger.info("Demo team created", extra={"team": settings.demo_team_name})

                # Demo session
                session_result = await db.execute(select(Session).where(Session.title == settings.demo_session_title))
                demo_session = session_result.scalar_one_or_none()
                if not demo_session:
                    session_service = SessionService(db)
                    demo_session = await session_service.create_session(
                        type("T", (), {"team_id": str(demo_team.id), "title": settings.demo_session_title, "description": "This is a demo session to help you explore BioLoupe.", "topic_tags": ["demo"]})(),
                        str(demo_user.id),
                    )
                    logger.info("Demo session created", extra={"session": settings.demo_session_title})
                await db.commit()
    except Exception as e:
        logger.warning(f"Demo seeding failed: {e}")

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
