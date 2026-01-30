from __future__ import annotations

import hashlib
import logging
from typing import Optional, Dict, Any, List
import numpy as np

from app.db.qdrant_client import get_qdrant_client
from app.services.reranking_service import ReRankingService
from app.services.cache_service import CacheService
from app.utils.search_filters import build_qdrant_filter

logger = logging.getLogger(__name__)


class SimilarityService:
    def __init__(self, cache: Optional[CacheService] = None) -> None:
        self._wrapper = get_qdrant_client()
        self._cache = cache or CacheService()
        self._rerank = ReRankingService()

    async def search_similar(
        self,
        collection: str,
        query_vector: np.ndarray,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        cache_key = self._generate_cache_key(collection, query_vector, filters, limit)
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        qdrant_filter = build_qdrant_filter(filters)

        # Qdrant client is sync-style on this wrapper; call with_retry to handle retries
        result = await self._wrapper.with_retry(
            self._wrapper.client.search,
            collection_name=collection,
            query_vector=query_vector.tolist(),
            query_filter=qdrant_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )

        formatted = []
        for r in result:
            score = float(r.score) if hasattr(r, "score") else 0.0
            # ensure normalized to [0,1]
            score = max(0.0, min(1.0, score))
            payload = r.payload or {}
            formatted.append(
                {
                    "material_id": payload.get("material_id"),
                    "score": score,
                    "modality": payload.get("modality"),
                    "title": payload.get("title"),
                    "content_preview": payload.get("content_preview"),
                    "metadata": payload.get("metadata"),
                    "session_id": payload.get("session_id"),
                    "indexed_at": payload.get("indexed_at"),
                    "explanation": None,
                }
            )

        # cache results
        await self._cache.set(cache_key, formatted, ttl=30 * 60)

        # basic reranking: recency
        formatted = self._rerank.rerank_by_recency(formatted)

        return formatted

    def _generate_cache_key(self, collection: str, vector: np.ndarray, filters: Optional[Dict], limit: int) -> str:
        vector_hash = hashlib.md5(np.asarray(vector).tobytes()).hexdigest()[:16]
        filter_hash = hashlib.md5(str(sorted(filters.items()) if filters else "").encode()).hexdigest()[:8]
        return f"search:{collection}:{vector_hash}:{filter_hash}:{limit}"
