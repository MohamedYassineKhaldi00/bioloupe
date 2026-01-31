from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.qdrant_config import (
    EXPERIMENTS_COLLECTION,
    PUBLICATIONS_COLLECTION,
    SEQUENCES_COLLECTION,
    UNIFIED_COLLECTION,
)
from app.models import Material, MaterialType, Session
from app.search.services.external_publications import ExternalPublicationClient
from app.services.embedding.paper_embedding import PaperEmbeddingService
from app.services.embedding.unified_embedding import UnifiedEmbeddingService
from app.core.ml_config import PAPER_EMBEDDING_CONFIG
from app.services.qdrant_service import QdrantService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class MaterialIngestionService:
    def __init__(
        self,
        db: AsyncSession,
        vector_service: VectorService | None = None,
        qdrant_service: QdrantService | None = None,
        external_client: ExternalPublicationClient | None = None,
    ) -> None:
        self._db = db
        self._settings = get_settings()
        self._vector = vector_service or VectorService()
        self._qdrant = qdrant_service or QdrantService()
        self._external = external_client or ExternalPublicationClient()
        self._unified = UnifiedEmbeddingService()
        self._paper_service: PaperEmbeddingService | None = None

    async def ingest_material(self, material: Material) -> dict[str, Any]:
        if self._settings.disable_vector_search:
            logger.info("Vector search disabled; skipping ingestion")
            return {"status": "skipped", "reason": "vector_search_disabled"}

        if self._settings.disable_embeddings:
            logger.info("Embeddings disabled; skipping ingestion")
            return {"status": "skipped", "reason": "embeddings_disabled"}

        session = None
        team_id = None
        if material.session_id:
            session = await self._db.get(Session, material.session_id)
            team_id = session.team_id if session else None

        # 1) Embed the uploaded material
        embedding = await self._embed_material(material)

        # 2) Upsert material vector to Qdrant
        collection = self._collection_for_material(material.material_type)
        payload = self._build_material_payload(material, team_id)
        await self._vector.upsert_vector(
            collection=collection,
            material_id=str(material.id),
            vector=embedding,
            payload=payload,
        )
        material.qdrant_point_id = material.id
        await self._db.flush()

        # 3) Fetch and index relevant publications (arXiv)
        publications = await self._fetch_relevant_publications(material)
        indexed = await self._index_publications(publications, material, team_id)

        # 4) Retrieve related publications for this material
        related = await self._find_related_publications(embedding)
        metadata = material.metadata_ or {}
        metadata["related_publications"] = related
        metadata["publication_indexed"] = indexed
        material.metadata_ = metadata
        await self._db.flush()

        return {
            "status": "ok",
            "collection": collection,
            "indexed_publications": indexed,
            "related_publications": len(related),
        }

    def _collection_for_material(self, material_type: MaterialType) -> str:
        if material_type == MaterialType.sequence:
            return SEQUENCES_COLLECTION.name
        if material_type == MaterialType.experiment:
            return EXPERIMENTS_COLLECTION.name
        return UNIFIED_COLLECTION.name

    async def _embed_material(self, material: Material):
        # Use text-based embedding for images to keep vector size consistent (768)
        if material.material_type == MaterialType.image:
            return await self._embed_image_as_text(material)
        return await self._unified.embed_material(material)

    async def _embed_image_as_text(self, material: Material):
        if self._paper_service is None:
            self._paper_service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
            await self._paper_service.load_model()

        metadata = material.metadata_ or {}
        description = metadata.get("description") or metadata.get("caption") or ""
        return await self._paper_service.embed_paper(title=material.title, abstract=description)

    def _build_material_payload(self, material: Material, team_id) -> dict[str, Any]:
        metadata = material.metadata_ or {}
        content_preview = (
            metadata.get("abstract")
            or metadata.get("description")
            or metadata.get("content")
            or ""
        )
        return {
            "material_id": str(material.id),
            "session_id": str(material.session_id) if material.session_id else None,
            "team_id": str(team_id) if team_id else None,
            "modality": material.material_type.value,
            "title": material.title,
            "content_preview": content_preview[:500],
            "metadata": metadata,
        }

    async def _fetch_relevant_publications(self, material: Material) -> list[dict[str, Any]]:
        query = material.title
        metadata = material.metadata_ or {}
        if metadata.get("abstract"):
            query = f"{query} {metadata.get('abstract')}"
        elif metadata.get("description"):
            query = f"{query} {metadata.get('description')}"
        elif metadata.get("content"):
            query = f"{query} {metadata.get('content')}"

        return await self._external.search_arxiv(query, page=1, limit=5)

    async def _index_publications(self, publications: list[dict[str, Any]], material: Material, team_id) -> int:
        if not publications:
            return 0

        if self._paper_service is None:
            self._paper_service = PaperEmbeddingService(PAPER_EMBEDDING_CONFIG)
            await self._paper_service.load_model()

        indexed = 0
        for record in publications:
            title = record.get("title", "")
            snippet = record.get("snippet") or ""
            publication_id = record.get("publication_id") or title
            try:
                embedding = await self._paper_service.embed_paper(title=title, abstract=snippet)
            except Exception as exc:
                logger.warning("Publication embedding failed", extra={"error": str(exc)})
                continue

            payload = {
                "material_id": str(publication_id),
                "session_id": str(material.session_id) if material.session_id else None,
                "team_id": str(team_id) if team_id else None,
                "modality": "publication",
                "title": title,
                "content_preview": snippet[:500],
                "metadata": record.get("metadata", {}),
                "source": "arxiv",
            }
            await self._vector.upsert_vector(
                collection=PUBLICATIONS_COLLECTION.name,
                material_id=str(publication_id),
                vector=embedding,
                payload=payload,
            )
            indexed += 1

        return indexed

    async def _find_related_publications(self, embedding) -> list[dict[str, Any]]:
        try:
            points = await self._qdrant.search_vectors(
                PUBLICATIONS_COLLECTION.name,
                embedding.tolist() if hasattr(embedding, "tolist") else list(embedding),
                limit=5,
            )
        except Exception as exc:
            logger.warning("Publication similarity search failed", extra={"error": str(exc)})
            return []

        results = []
        for point in points:
            payload = point.payload or {}
            results.append(
                {
                    "publication_id": payload.get("material_id") or payload.get("publication_id"),
                    "title": payload.get("title"),
                    "score": float(point.score) if point.score is not None else 0.0,
                    "source": payload.get("source", "arxiv"),
                }
            )
        return results
