"""Qdrant operations for embedding storage."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import numpy as np
from qdrant_client.http import models as rest

from app.core.qdrant_config import UNIFIED_COLLECTION
from app.db.qdrant_client import get_qdrant_client
from app.models.material import Material

logger = logging.getLogger(__name__)


class EmbeddingStorageService:
    """Handles storage and retrieval of embeddings in Qdrant."""

    def __init__(self) -> None:
        """Initialize embedding storage service."""
        self._qdrant = get_qdrant_client()

    async def upsert_embedding(
        self,
        material: Material,
        embedding: np.ndarray,
        collection_name: str | None = None,
    ) -> uuid.UUID:
        """Upsert embedding to Qdrant.

        Args:
            material: Material with metadata
            embedding: Embedding vector
            collection_name: Optional collection name (defaults to unified)

        Returns:
            Point ID assigned in Qdrant

        Raises:
            Exception: If upsert fails
        """
        collection = collection_name or UNIFIED_COLLECTION.name
        point_id = material.qdrant_point_id or uuid.uuid4()

        payload = self._build_payload(material)

        point = rest.PointStruct(
            id=str(point_id),
            vector=embedding.tolist(),
            payload=payload,
        )

        await self._qdrant.with_retry(
            self._qdrant.client.upsert,
            collection_name=collection,
            points=[point],
        )

        logger.info(f"Upserted embedding for material {material.id} to {collection}")
        return point_id

    async def batch_upsert(
        self,
        materials: list[Material],
        embeddings: dict[str, np.ndarray],
        collection_name: str | None = None,
    ) -> dict[str, uuid.UUID]:
        """Batch upsert embeddings to Qdrant.

        Args:
            materials: List of materials
            embeddings: Dict mapping material IDs to embeddings
            collection_name: Optional collection name

        Returns:
            Dict mapping material IDs to point IDs
        """
        collection = collection_name or UNIFIED_COLLECTION.name
        points = []
        point_ids = {}

        for material in materials:
            mat_id = str(material.id)
            if mat_id not in embeddings:
                continue

            point_id = material.qdrant_point_id or uuid.uuid4()
            point_ids[mat_id] = point_id

            payload = self._build_payload(material)
            points.append(
                rest.PointStruct(
                    id=str(point_id),
                    vector=embeddings[mat_id].tolist(),
                    payload=payload,
                )
            )

        if points:
            await self._qdrant.with_retry(
                self._qdrant.client.upsert,
                collection_name=collection,
                points=points,
            )

            logger.info(f"Batch upserted {len(points)} embeddings to {collection}")

        return point_ids

    async def delete_embedding(
        self,
        point_id: uuid.UUID,
        collection_name: str | None = None,
    ) -> None:
        """Delete embedding from Qdrant.

        Args:
            point_id: Point ID to delete
            collection_name: Optional collection name
        """
        collection = collection_name or UNIFIED_COLLECTION.name

        await self._qdrant.with_retry(
            self._qdrant.client.delete,
            collection_name=collection,
            points_selector=rest.PointIdsList(points=[str(point_id)]),
        )

        logger.info(f"Deleted point {point_id} from {collection}")

    async def search_similar(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        collection_name: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[rest.ScoredPoint]:
        """Search for similar embeddings.

        Args:
            query_embedding: Query vector
            limit: Number of results to return
            collection_name: Optional collection name
            filters: Optional Qdrant filters

        Returns:
            List of scored points
        """
        collection = collection_name or UNIFIED_COLLECTION.name

        query_filter = self._build_filter(filters) if filters else None

        results = await self._qdrant.with_retry(
            self._qdrant.client.search,
            collection_name=collection,
            query_vector=query_embedding.tolist(),
            limit=limit,
            query_filter=query_filter,
        )

        return results

    def _build_payload(self, material: Material) -> dict[str, Any]:
        """Build Qdrant payload from material.

        Args:
            material: Material model

        Returns:
            Payload dict
        """
        payload = {
            "material_id": str(material.id),
            "session_id": str(material.session_id),
            "material_type": material.material_type.value,
            "title": material.title,
        }

        if material.uploaded_by_id:
            payload["uploaded_by_id"] = str(material.uploaded_by_id)

        if material.metadata_:
            payload["metadata"] = material.metadata_

        return payload

    def _build_filter(self, filters: dict[str, Any]) -> rest.Filter:
        """Build Qdrant filter from dict.

        Args:
            filters: Filter parameters

        Returns:
            Qdrant Filter object
        """
        must_conditions = []

        for key, value in filters.items():
            must_conditions.append(
                rest.FieldCondition(
                    key=key,
                    match=rest.MatchValue(value=value),
                )
            )

        return rest.Filter(must=must_conditions)
