from __future__ import annotations

import logging
from typing import Iterable
from qdrant_client.http import models as rest

from app.core.exceptions import VectorDBException
from app.db.qdrant_client import QdrantClientWrapper, get_qdrant_client

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self, client_wrapper: QdrantClientWrapper | None = None) -> None:
        self._wrapper = client_wrapper or get_qdrant_client()

    async def upsert_vectors(
        self,
        collection: str,
        points: list[rest.PointStruct],
        batch_size: int = 100,
    ) -> rest.UpdateResult:
        if not points:
            raise VectorDBException("No vectors to upsert")

        results: list[rest.UpdateResult] = []
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                result = await self._wrapper.with_retry(
                    self._wrapper.client.upsert,
                    collection_name=collection,
                    points=batch,
                    wait=True,
                )
                results.append(result)
            except Exception as exc:
                logger.error("Qdrant upsert failed", extra={"error": str(exc)})
                raise VectorDBException(f"Failed to upsert vectors: {exc}") from exc

        return results[-1]

    async def search_vectors(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        query_filter: rest.Filter | None = None,
    ) -> list[rest.ScoredPoint]:
        try:
            result = await self._wrapper.with_retry(
                self._wrapper.client.search,
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                with_payload=True,
            )
            return result
        except Exception as exc:
            logger.error("Qdrant search failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to search vectors: {exc}") from exc

    async def delete_points(
        self,
        collection: str,
        point_ids: Iterable[str],
    ) -> rest.UpdateResult:
        ids = list(point_ids)
        if not ids:
            raise VectorDBException("No point IDs provided")

        try:
            return await self._wrapper.with_retry(
                self._wrapper.client.delete,
                collection_name=collection,
                points_selector=rest.PointIdsList(points=ids),
                wait=True,
            )
        except Exception as exc:
            logger.error("Qdrant delete failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to delete vectors: {exc}") from exc

    async def collection_info(self, collection: str) -> rest.CollectionInfo:
        try:
            return await self._wrapper.with_retry(
                self._wrapper.client.get_collection,
                collection_name=collection,
            )
        except Exception as exc:
            logger.error("Qdrant collection info failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to get collection info: {exc}") from exc

    async def collection_stats(self, collection: str) -> rest.CollectionInfo:
        try:
            return await self._wrapper.with_retry(
                self._wrapper.client.get_collection,
                collection_name=collection,
            )
        except Exception as exc:
            logger.error("Qdrant collection stats failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to get collection stats: {exc}") from exc

    async def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: rest.Distance,
    ) -> None:
        try:
            await self._wrapper.with_retry(
                self._wrapper.client.create_collection,
                collection_name=name,
                vectors_config=rest.VectorParams(size=vector_size, distance=distance),
            )
        except Exception as exc:
            logger.error("Qdrant create collection failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to create collection: {exc}") from exc

    async def delete_collection(self, collection: str) -> None:
        try:
            await self._wrapper.with_retry(
                self._wrapper.client.delete_collection,
                collection_name=collection,
            )
        except Exception as exc:
            logger.error("Qdrant delete collection failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to delete collection: {exc}") from exc

    async def update_collection_config(
        self,
        collection: str,
        quantization_config: rest.QuantizationConfig | None = None,
        hnsw_config: rest.HnswConfigDiff | None = None,
    ) -> None:
        if quantization_config is None and hnsw_config is None:
            return
        try:
            await self._wrapper.with_retry(
                self._wrapper.client.update_collection,
                collection_name=collection,
                quantization_config=quantization_config,
                hnsw_config=hnsw_config,
            )
        except Exception as exc:
            logger.error("Qdrant update collection failed", extra={"error": str(exc)})
            raise VectorDBException(f"Failed to update collection config: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            await self._wrapper.with_retry(self._wrapper.client.get_collections)
            return True
        except Exception as exc:
            logger.error("Qdrant health check failed", extra={"error": str(exc)})
            return False
