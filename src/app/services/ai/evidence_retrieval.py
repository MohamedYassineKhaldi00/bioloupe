"""
Evidence Retrieval Service for Hypothesis Generation.

Retrieves similar experiments and literature from vector store
to support evidence-based hypothesis generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client.http import models as rest

from app.services.qdrant_service import QdrantService
from app.services.session_service import SessionService
from app.services.material_service import MaterialService

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """
    Retrieves evidence from vector database to support hypothesis generation.

    Finds similar experiments, papers, and materials based on:
    - Session materials embeddings
    - Research goal embeddings
    - Filter criteria (peer-reviewed, successful outcomes, etc.)
    """

    def __init__(
        self,
        qdrant_service: QdrantService,
        session_service: SessionService,
        material_service: MaterialService,
    ):
        self.qdrant = qdrant_service
        self.session_service = session_service
        self.material_service = material_service

    async def find_similar_experiments(
        self,
        session_id: UUID,
        filter_criteria: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Find similar experiments from literature based on session materials.

        Args:
            session_id: Session to analyze
            filter_criteria: Filter for results (e.g., {'outcome': 'successful', 'peer_reviewed': True})
            limit: Maximum number of similar experiments to retrieve

        Returns:
            List of similar experiment dictionaries with metadata and scores
        """
        logger.info(
            "Finding similar experiments",
            extra={"session_id": str(session_id), "limit": limit},
        )

        # Get session materials
        materials = await self.material_service.get_materials_by_session(session_id)

        if not materials:
            logger.warning("No materials found for session", extra={"session_id": str(session_id)})
            return []

        # Get embeddings for materials (papers, sequences, images)
        material_vectors = await self._get_material_vectors(materials)

        if not material_vectors:
            logger.warning("No vectors found for session materials")
            return []

        # Average vectors to create session representation
        avg_vector = self._average_vectors(material_vectors)

        # Build Qdrant filter from criteria
        query_filter = self._build_filter(filter_criteria) if filter_criteria else None

        # Search across relevant collections
        similar_experiments = []

        # Search papers collection
        papers_results = await self.qdrant.search_vectors(
            collection="papers",
            query_vector=avg_vector,
            limit=limit,
            query_filter=query_filter,
        )

        for result in papers_results:
            similar_experiments.append({
                "type": "paper",
                "id": result.id,
                "score": result.score,
                "metadata": result.payload or {},
                "title": result.payload.get("title", "") if result.payload else "",
                "abstract": result.payload.get("abstract", "") if result.payload else "",
                "methods": result.payload.get("methods", "") if result.payload else "",
                "results": result.payload.get("results", "") if result.payload else "",
            })

        logger.info(
            "Found similar experiments",
            extra={"count": len(similar_experiments), "session_id": str(session_id)},
        )

        return similar_experiments

    async def find_related_materials(
        self,
        query_vector: List[float],
        material_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Find related materials based on query vector.

        Args:
            query_vector: Query embedding vector
            material_type: Filter by material type (paper, sequence, image)
            limit: Maximum results

        Returns:
            List of related materials with metadata
        """
        query_filter = None
        if material_type:
            query_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="material_type",
                        match=rest.MatchValue(value=material_type),
                    )
                ]
            )

        results = await self.qdrant.search_vectors(
            collection="materials",
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
        )

        materials = []
        for result in results:
            materials.append({
                "id": result.id,
                "score": result.score,
                "type": result.payload.get("material_type") if result.payload else None,
                "metadata": result.payload or {},
            })

        return materials

    async def get_session_context(self, session_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive context about a research session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session metadata, materials, and statistics
        """
        session = await self.session_service.get_session_by_id(session_id)
        materials = await self.material_service.get_materials_by_session(session_id)

        # Count materials by type
        material_counts = {}
        for material in materials:
            mat_type = material.material_type
            material_counts[mat_type] = material_counts.get(mat_type, 0) + 1

        return {
            "session_id": str(session_id),
            "title": session.title if session else "",
            "description": session.description if session else "",
            "materials_count": len(materials),
            "materials_by_type": material_counts,
            "materials": [
                {
                    "id": str(material.id),
                    "type": material.material_type,
                    "title": material.title,
                    "metadata": material.metadata or {},
                }
                for material in materials
            ],
        }

    async def _get_material_vectors(self, materials: List[Any]) -> List[List[float]]:
        """Extract embedding vectors from materials."""
        vectors = []

        for material in materials:
            # Try to get vector from Qdrant
            try:
                # Search for this material's vector
                # Material ID should be stored as point ID in Qdrant
                collection = self._get_collection_for_material_type(material.material_type)

                # For now, skip if we can't determine collection
                # In production, you'd retrieve the actual stored vector
                if collection:
                    logger.debug(
                        "Material vector retrieval",
                        extra={
                            "material_id": str(material.id),
                            "type": material.material_type,
                            "collection": collection,
                        },
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to get vector for material",
                    extra={"material_id": str(material.id), "error": str(exc)},
                )
                continue

        return vectors

    def _get_collection_for_material_type(self, material_type: str) -> Optional[str]:
        """Map material type to Qdrant collection name."""
        mapping = {
            "paper": "papers",
            "sequence": "sequences",
            "image": "images",
        }
        return mapping.get(material_type)

    def _average_vectors(self, vectors: List[List[float]]) -> List[float]:
        """Calculate average of multiple vectors."""
        if not vectors:
            raise ValueError("Cannot average empty vector list")

        if len(vectors) == 1:
            return vectors[0]

        # Calculate element-wise average
        vector_length = len(vectors[0])
        avg_vector = [0.0] * vector_length

        for vec in vectors:
            for i, val in enumerate(vec):
                avg_vector[i] += val

        for i in range(vector_length):
            avg_vector[i] /= len(vectors)

        return avg_vector

    def _build_filter(self, criteria: Dict[str, Any]) -> rest.Filter:
        """Build Qdrant filter from criteria dictionary."""
        conditions = []

        for key, value in criteria.items():
            if isinstance(value, bool):
                conditions.append(
                    rest.FieldCondition(
                        key=key,
                        match=rest.MatchValue(value=value),
                    )
                )
            elif isinstance(value, str):
                conditions.append(
                    rest.FieldCondition(
                        key=key,
                        match=rest.MatchValue(value=value),
                    )
                )
            elif isinstance(value, (int, float)):
                conditions.append(
                    rest.FieldCondition(
                        key=key,
                        match=rest.MatchValue(value=value),
                    )
                )

        return rest.Filter(must=conditions) if conditions else rest.Filter()
