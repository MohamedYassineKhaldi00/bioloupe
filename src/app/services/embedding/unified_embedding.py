"""Unified embedding service with multi-modal routing."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmbeddingError
from app.core.ml_config import (
    IMAGE_EMBEDDING_CONFIG,
    PAPER_EMBEDDING_CONFIG,
    SEQUENCE_EMBEDDING_CONFIG,
)
from app.db.redis_client import get_redis
from app.models.material import Material, MaterialType
from app.services.embedding.base import BaseEmbeddingService
from app.services.embedding.fusion import EmbeddingFusion, FusionMethod
from app.services.embedding.image_embedding import ImageEmbeddingService
from app.services.embedding.paper_embedding import PaperEmbeddingService
from app.services.embedding.sequence_embedding import SequenceEmbeddingService
from app.services.embedding.storage import EmbeddingStorageService

logger = logging.getLogger(__name__)

EMBEDDING_CACHE_TTL = 3600  # 1 hour


class UnifiedEmbeddingService:
    """Routes embedding requests to appropriate service."""

    def __init__(self) -> None:
        """Initialize unified embedding service."""
        self._paper_service: PaperEmbeddingService | None = None
        self._sequence_service: SequenceEmbeddingService | None = None
        self._image_service: ImageEmbeddingService | None = None
        self._fusion = EmbeddingFusion()
        self._storage = EmbeddingStorageService()

    async def _get_paper_service(self) -> PaperEmbeddingService:
        """Get or initialize paper embedding service."""
        if self._paper_service is None:
            self._paper_service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
            await self._paper_service.load_model()
        return self._paper_service

    async def _get_sequence_service(self) -> SequenceEmbeddingService:
        """Get or initialize sequence embedding service."""
        if self._sequence_service is None:
            self._sequence_service = SequenceEmbeddingService(SEQUENCE_EMBEDDING_CONFIG)
            await self._sequence_service.load_model()
        return self._sequence_service

    async def _get_image_service(self) -> ImageEmbeddingService:
        """Get or initialize image embedding service."""
        if self._image_service is None:
            self._image_service = ImageEmbeddingService(IMAGE_EMBEDDING_CONFIG)
            await self._image_service.load_model()
        return self._image_service

    async def route_to_service(
        self,
        material_type: MaterialType
    ) -> BaseEmbeddingService:
        """Route to appropriate embedding service.

        Args:
            material_type: Type of material

        Returns:
            Appropriate embedding service

        Raises:
            ValueError: If material type not supported
        """
        if material_type == MaterialType.paper:
            return await self._get_paper_service()
        elif material_type == MaterialType.sequence:
            return await self._get_sequence_service()
        elif material_type == MaterialType.image:
            return await self._get_image_service()
        elif material_type == MaterialType.experiment:
            return await self._get_paper_service()
        elif material_type == MaterialType.note:
            return await self._get_paper_service()
        else:
            raise ValueError(f"Unsupported material type: {material_type}")

    async def embed_material(
        self,
        material: Material
    ) -> np.ndarray:
        """Generate embedding for material.

        Args:
            material: Material to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding fails
        """
        cached = await self._get_cached_embedding(material.id)
        if cached is not None:
            return cached

        try:
            service = await self.route_to_service(material.material_type)

            if material.material_type == MaterialType.paper:
                embedding = await service.embed_from_metadata(material)  # type: ignore
            elif material.material_type == MaterialType.sequence:
                embedding = await service.embed_from_material(material)  # type: ignore
            elif material.material_type == MaterialType.image:
                embedding = await self._embed_image_material(material, service)
            elif material.material_type == MaterialType.experiment:
                embedding = await self._embed_experiment(material, service)
            elif material.material_type == MaterialType.note:
                embedding = await self._embed_note(material, service)
            else:
                raise ValueError(f"Unsupported material type: {material.material_type}")

            await self._cache_embedding(material.id, embedding)
            return embedding

        except Exception as e:
            logger.error(f"Embedding failed for material {material.id}: {e}")
            raise EmbeddingError(f"Failed to embed material: {str(e)}")

    async def embed_batch(
        self,
        materials: list[Material]
    ) -> dict[str, np.ndarray]:
        """Generate embeddings for batch of materials.

        Args:
            materials: List of materials to embed

        Returns:
            Dict mapping material IDs to embeddings

        Raises:
            EmbeddingError: If batch embedding fails
        """
        results: dict[str, np.ndarray] = {}

        grouped = self._group_by_type(materials)

        for material_type, type_materials in grouped.items():
            try:
                service = await self.route_to_service(material_type)
                type_embeddings = await self._embed_group(
                    type_materials, service
                )
                results.update(type_embeddings)
            except Exception as e:
                logger.error(f"Batch embedding failed for {material_type}: {e}")

        return results

    def _group_by_type(
        self,
        materials: list[Material]
    ) -> dict[MaterialType, list[Material]]:
        """Group materials by type."""
        groups: dict[MaterialType, list[Material]] = {}
        for material in materials:
            groups.setdefault(material.material_type, []).append(material)
        return groups

    async def _embed_group(
        self,
        materials: list[Material],
        service: BaseEmbeddingService
    ) -> dict[str, np.ndarray]:
        """Embed group of materials with same service."""
        results = {}
        for material in materials:
            try:
                embedding = await self.embed_material(material)
                results[str(material.id)] = embedding
            except Exception as e:
                logger.error(f"Failed to embed material {material.id}: {e}")
        return results

    async def _embed_image_material(
        self,
        material: Material,
        service: BaseEmbeddingService
    ) -> np.ndarray:
        """Embed image material from file URL."""
        from PIL import Image

        if not material.file_url:
            raise EmbeddingError("Image material has no file URL")

        image = Image.open(material.file_url)
        return await service.embed(image)

    async def _embed_experiment(
        self,
        material: Material,
        service: PaperEmbeddingService
    ) -> np.ndarray:
        """Embed experiment using text description."""
        metadata = material.metadata_ or {}
        description = metadata.get("description", "")

        return await service.embed_paper(
            title=material.title,
            abstract=description
        )

    async def _embed_note(
        self,
        material: Material,
        service: PaperEmbeddingService
    ) -> np.ndarray:
        """Embed note using text content."""
        metadata = material.metadata_ or {}
        content = metadata.get("content", "")

        return await service.embed_paper(
            title=material.title,
            abstract=content
        )

    async def _get_cached_embedding(
        self,
        material_id: uuid.UUID
    ) -> np.ndarray | None:
        """Retrieve cached embedding."""
        try:
            redis = get_redis()
            cache_key = f"embedding:{material_id}"
            cached_bytes = await redis.get(cache_key)

            if cached_bytes:
                return np.frombuffer(cached_bytes, dtype=np.float32)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    async def _cache_embedding(
        self,
        material_id: uuid.UUID,
        embedding: np.ndarray
    ) -> None:
        """Cache embedding in Redis."""
        try:
            redis = get_redis()
            cache_key = f"embedding:{material_id}"
            embedding_bytes = embedding.astype(np.float32).tobytes()
            await redis.setex(cache_key, EMBEDDING_CACHE_TTL, embedding_bytes)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    async def invalidate_cache(self, material_id: uuid.UUID) -> None:
        """Invalidate cached embedding."""
        try:
            redis = get_redis()
            cache_key = f"embedding:{material_id}"
            await redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

    async def embed_and_upsert(
        self,
        material: Material,
        collection_name: str | None = None,
    ) -> uuid.UUID:
        """Generate embedding and upsert to Qdrant.

        Args:
            material: Material to embed
            collection_name: Optional collection name

        Returns:
            Qdrant point ID

        Raises:
            EmbeddingError: If operation fails
        """
        try:
            embedding = await self.embed_material(material)
            point_id = await self._storage.upsert_embedding(
                material, embedding, collection_name
            )
            return point_id

        except Exception as e:
            logger.error(f"Embed and upsert failed for {material.id}: {e}")
            raise EmbeddingError(f"Failed to embed and upsert: {str(e)}")
