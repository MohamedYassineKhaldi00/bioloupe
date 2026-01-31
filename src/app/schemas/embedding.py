"""Schemas for embedding endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResponse(BaseModel):
    """Response schema for single embedding."""

    model_config = ConfigDict(protected_namespaces=())

    material_id: uuid.UUID
    embedding: list[float]
    dimension: int
    model_name: str
    cached: bool = False


class BatchEmbeddingRequest(BaseModel):
    """Request schema for batch embedding."""

    material_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=1000)


class BatchEmbeddingResponse(BaseModel):
    """Response schema for batch embedding."""

    embeddings: dict[str, list[float]]
    successful: int
    failed: int
    errors: dict[str, str] = Field(default_factory=dict)


class ReindexRequest(BaseModel):
    """Request schema for reindexing materials."""

    batch_size: int = Field(default=1000, ge=1, le=10000)
    material_types: list[str] | None = None


class ReindexResponse(BaseModel):
    """Response schema for reindex operation."""

    task_id: str
    total_materials: int
    message: str


class EmbeddingStatsResponse(BaseModel):
    """Response schema for embedding statistics."""

    total_embeddings: int
    by_type: dict[str, int]
    cache_hit_rate: float
    avg_generation_time_ms: float


class EmbeddingMetrics(BaseModel):
    """Embedding quality metrics."""

    material_id: uuid.UUID
    generation_time_ms: float
    model_name: str
    dimension: int
    metadata: dict[str, Any] = Field(default_factory=dict)
