from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
import numpy as np

from qdrant_client.http import models as rest

from app.db.qdrant_client import get_qdrant_client
from app.utils.vector_validators import validate_vector_dimensions, validate_payload_metadata
from app.core.vector_exceptions import VectorUpsertFailed, CollectionNotFound, VectorDimensionMismatch
from app.services.vector_enrichment import enrich_payload

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self) -> None:
        self._wrapper = get_qdrant_client()

    async def upsert_vector(
        self,
        collection: str,
        material_id: str,
        vector: List[float] | np.ndarray,
        payload: Dict[str, Any],
    ) -> bool:
        try:
            # Validate
            validate_vector_dimensions(collection, vector)
            validate_payload_metadata(payload)

            enriched = enrich_payload(payload)

            vec_list = vector.tolist() if isinstance(vector, np.ndarray) else list(vector)

            # Use plain dict points to be resilient across qdrant-client versions
            point = {"id": material_id, "vector": vec_list, "payload": enriched}

            await self._wrapper.with_retry(
                self._wrapper.client.upsert,
                collection_name=collection,
                points=[point],
                wait=True,
            )

            logger.info("Upserted vector", extra={"material_id": material_id, "collection": collection})
            return True
        except CollectionNotFound:
            raise
        except VectorDimensionMismatch:
            # Surface dimension errors directly for callers/tests to handle
            raise
        except Exception as exc:
            logger.error("Vector upsert failed", exc_info=True, extra={"material_id": material_id})
            raise VectorUpsertFailed(material_id, str(exc)) from exc

    async def batch_upsert(
        self,
        collection: str,
        points: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            qdrant_points = []
            for p in batch:
                validate_vector_dimensions(collection, p["vector"])
                validate_payload_metadata(p.get("payload", {}))
                vec = p["vector"].tolist() if isinstance(p["vector"], np.ndarray) else list(p["vector"])
                enriched = enrich_payload(p.get("payload", {}))
                qdrant_points.append({"id": p["id"], "vector": vec, "payload": enriched})

            try:
                await self._wrapper.with_retry(
                    self._wrapper.client.upsert,
                    collection_name=collection,
                    points=qdrant_points,
                    wait=True,
                )
                total_upserted += len(batch)
            except Exception as exc:
                logger.error("Batch upsert failed", exc_info=True, extra={"start_index": i, "error": str(exc)})
                # Stop and bubble up as VectorUpsertFailed
                raise VectorUpsertFailed("batch", str(exc)) from exc

        return total_upserted

    async def delete_vector(self, collection: str, material_id: str) -> bool:
        try:
            try:
                selector = rest.PointIdsList(points=[material_id])
            except Exception:
                selector = {"ids": [material_id]}

            await self._wrapper.with_retry(
                self._wrapper.client.delete,
                collection_name=collection,
                points_selector=selector,
                wait=True,
            )
            return True
        except Exception as exc:
            logger.error("Vector deletion failed", exc_info=True, extra={"material_id": material_id})
            return False
