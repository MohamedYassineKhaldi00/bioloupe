from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import List

from app.search.models.similarity_models import (
    SimilarityExplorationRequest,
    SimilarityExplorationResponse,
    SimilarityItem,
    SimilarityExplanation,
    TemporalBucket,
)
from app.search.utils.explanation import build_similarity_explanation
from app.services.cache_service import CacheService
from app.services.qdrant_service import QdrantService


class SimilarityExplorationService:
    def __init__(self, vector_service: QdrantService, cache: CacheService | None = None) -> None:
        self._vector_service = vector_service
        self._cache = cache or CacheService()

    async def explore(self, request: SimilarityExplorationRequest) -> SimilarityExplorationResponse:
        cache_key = f"search:similarity:{request.collection}:{request.material_id or hash(tuple(request.query_vector or [])):x}:{request.limit}:{request.timeframe_days}"
        cached = await self._cache.get(cache_key)
        if isinstance(cached, dict):
            return SimilarityExplorationResponse(**cached)

        vector = request.query_vector or self._pseudo_vector(request.material_id or "")
        points = await self._vector_service.search_vectors(request.collection, vector, limit=request.limit)
        baseline_tags = []
        explanation_results: List[SimilarityItem] = []
        for point in points:
            payload = point.payload or {}
            tags = payload.get("metadata", {}).get("tags", []) if isinstance(payload.get("metadata"), dict) else []
            explanation = build_similarity_explanation(baseline_tags, tags, float(point.score) if point.score else 0.0)
            explanation_results.append(
                SimilarityItem(
                    material_id=str(payload.get("material_id")),
                    title=str(payload.get("title", "")),
                    score=float(point.score) if point.score else 0.0,
                    modality=payload.get("modality"),
                    metadata=payload,
                    explanation=SimilarityExplanation(**explanation),
                    indexed_at=payload.get("indexed_at"),
                )
            )

        temporal = self._build_temporal_summary(explanation_results, request.timeframe_days)
        response = SimilarityExplorationResponse(
            results=explanation_results,
            temporal_summary=temporal,
            reference_material=request.material_id,
            total=len(explanation_results),
        )
        await self._cache.set(cache_key, response.model_dump(), ttl=300)
        return response

    def _pseudo_vector(self, key: str) -> List[float]:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return [byte / 255.0 for byte in digest[:32]]

    def _build_temporal_summary(self, results: List[SimilarityItem], window_days: int) -> List[TemporalBucket]:
        now = datetime.now(timezone.utc)
        buckets = defaultdict(int)
        for result in results:
            if not result.indexed_at:
                buckets["unknown"] += 1
                continue
            try:
                ts = result.indexed_at
                if ts.endswith("Z"):
                    ts = ts.replace("Z", "+00:00")
                point_time = datetime.fromisoformat(ts)
                delta = now - point_time
                age = delta.days
                bucket_key = self._bucket_label(age, window_days)
                buckets[bucket_key] += 1
            except Exception:
                buckets["unknown"] += 1
        summaries: List[TemporalBucket] = []
        for label, count in buckets.items():
            summaries.append(TemporalBucket(window_start=label, window_end=label, count=count))
        return summaries

    def _bucket_label(self, age_days: int, window_days: int) -> str:
        if age_days <= min(7, window_days):
            return "recent"
        if age_days <= min(30, window_days):
            return "mid"
        if age_days <= window_days:
            return "older"
        return "stale"
