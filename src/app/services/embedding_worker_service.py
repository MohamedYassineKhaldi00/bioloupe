from __future__ import annotations

import uuid
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class EmbeddingWorkerService:
    def __init__(self, db: AsyncSession, vector_service, embedding_service: Optional[EmbeddingService] = None):
        self.db = db
        self.vector_service = vector_service
        self.embedding_service = embedding_service or EmbeddingService()

    async def generate_material_embedding(self, material_id: str) -> dict:
        # This function expects the caller to provide a ready DB session or mocks in tests
        # Minimal implementation: fetch material, call embedding, upsert to vector service
        try:
            # Fetch material from DB — to be mocked in tests
            material = await self._get_material(material_id)

            if material is None:
                raise ValueError("Material not found")

            title = getattr(material, "title", "")
            abstract = None
            metadata = getattr(material, "metadata_", None) or {}
            abstract = metadata.get("abstract")

            embedding = await self.embedding_service.embed_paper(title=title, abstract=abstract, full_text=None)

            point_id = str(uuid.uuid4())
            await self.vector_service.upsert_vector(
                collection="bioloupe_publications",
                point_id=point_id,
                vector=embedding,
                payload={"material_id": str(getattr(material, "id", "")), "title": title}
            )

            # Update material.qdrant_point_id (DB write expected to be mocked)
            try:
                material.qdrant_point_id = point_id
                self.db.add(material)
                await self.db.commit()
            except Exception:
                logger.warning("Failed to persist qdrant_point_id; continuing")

            return {"material_id": str(getattr(material, "id", "")), "point_id": point_id}
        except Exception as e:
            logger.exception("Error generating embedding for %s: %s", material_id, e)
            raise

    async def _get_material(self, material_id: str) -> Any:
        # Minimal DB fetch — to be mocked in tests
        result = await self.db.execute("SELECT * FROM materials WHERE id = :id", {"id": material_id})
        # Return a simple object-like record or None
        row = result.first()
        return row
