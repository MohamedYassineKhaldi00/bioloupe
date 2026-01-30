from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, root_validator, constr


class SimilarityExplorationRequest(BaseModel):
    collection: str
    query_vector: Optional[List[float]] = None
    material_id: Optional[str] = None
    modality_filter: Optional[List[str]] = None
    timeframe_days: int = Field(default=30, ge=1)
    limit: int = Field(default=12, ge=1, le=50)

    @root_validator
    def require_vector_or_material(cls, values):
        if not values.get("query_vector") and not values.get("material_id"):
            raise ValueError("query_vector or material_id is required")
        return values


class SimilarityExplanation(BaseModel):
    shared_tags: List[str] = Field(default_factory=list)
    embedding_similarity: float
    why: Optional[str] = None


class TemporalBucket(BaseModel):
    window_start: str
    window_end: str
    count: int


class SimilarityItem(BaseModel):
    material_id: str
    title: str
    score: float
    modality: Optional[str]
    metadata: Dict[str, Any]
    explanation: SimilarityExplanation
    indexed_at: Optional[str]


class SimilarityExplorationResponse(BaseModel):
    results: List[SimilarityItem]
    temporal_summary: List[TemporalBucket]
    reference_material: Optional[str]
    total: int
