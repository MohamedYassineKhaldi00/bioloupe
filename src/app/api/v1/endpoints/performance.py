from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, constr

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.common import DBSessionDep
from app.services.performance_cache import PerformanceCacheService
from app.services.query_monitor import QueryMonitorService
from app.services.throttling_service import ThrottlingService
from app.services.vector_optimization import VectorOptimizationService
from app.services.qdrant_service import QdrantService

router = APIRouter(prefix="/performance", tags=["performance"])


def get_performance_cache_service() -> PerformanceCacheService:
    return PerformanceCacheService()


def get_vector_optimization_service(
    cache: PerformanceCacheService = Depends(get_performance_cache_service),
) -> VectorOptimizationService:
    return VectorOptimizationService(QdrantService(), cache)


def get_query_monitor_service() -> QueryMonitorService:
    return QueryMonitorService()


def get_throttling_service() -> ThrottlingService:
    return ThrottlingService()


class CacheMetricsResponse(BaseModel):
    metrics: dict[str, Any]


class QueryExplainRequest(BaseModel):
    sql: constr(min_length=5)


class QueryExplainResponse(BaseModel):
    plan: list[str]


@router.get("/cache/metrics", response_model=CacheMetricsResponse)
async def cache_metrics(
    cache: PerformanceCacheService = Depends(get_performance_cache_service),
    throttler: ThrottlingService = Depends(get_throttling_service),
    user=Depends(get_current_active_user),
) -> CacheMetricsResponse:
    await throttler.enforce_user(str(user.id))
    metrics = await cache.get_cache_metrics()
    return CacheMetricsResponse(metrics=metrics)


@router.get("/vector/{collection}")
async def vector_metrics(
    collection: str,
    service: VectorOptimizationService = Depends(get_vector_optimization_service),
    throttler: ThrottlingService = Depends(get_throttling_service),
    user=Depends(get_current_active_user),
) -> dict[str, Any]:
    await throttler.enforce_user(str(user.id))
    return await service.monitor_collection(collection)


@router.post("/query/explain", response_model=QueryExplainResponse)
async def explain_query(
    payload: QueryExplainRequest,
    session: AsyncSession = Depends(DBSessionDep),
    service: QueryMonitorService = Depends(get_query_monitor_service),
    throttler: ThrottlingService = Depends(get_throttling_service),
    user=Depends(get_current_active_user),
) -> QueryExplainResponse:
    await throttler.enforce_user(str(user.id))
    plan = await service.explain(session, payload.sql)
    return QueryExplainResponse(plan=plan)
