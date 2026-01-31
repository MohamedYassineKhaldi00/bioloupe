from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.db.base import verify_connection
from app.db.redis_client import get_redis
from app.services.qdrant_service import QdrantService

router = APIRouter(prefix="/health", tags=["health"])


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    redis: str
    qdrant: str


@router.get("", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    db_status = "healthy"
    redis_status = "healthy"
    qdrant_status = "healthy"
    
    try:
        await verify_connection()
    except Exception:
        db_status = "unhealthy"
    
    try:
        redis = get_redis()
        await redis.ping()
    except Exception:
        redis_status = "unhealthy"
    
    try:
        qdrant_service = QdrantService()
        is_healthy = await qdrant_service.health_check()
        if not is_healthy:
            qdrant_status = "unhealthy"
    except Exception:
        qdrant_status = "unhealthy"
    
    overall_status = "healthy"
    if db_status == "unhealthy" or redis_status == "unhealthy" or qdrant_status == "unhealthy":
        overall_status = "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        database=db_status,
        redis=redis_status,
        qdrant=qdrant_status,
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, str]:
    try:
        await verify_connection()
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}
