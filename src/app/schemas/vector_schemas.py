from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

import numpy as np


class VectorMetadata(BaseModel):
    material_id: str
    session_id: str
    team_id: str
    modality: str
    title: Optional[str] = None
    content_preview: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    indexed_at: Optional[str] = None
    embedding_model: Optional[str] = None


class VectorPayload(BaseModel):
    id: str = Field(..., alias="material_id")
    vector: List[float]
    payload: VectorMetadata


class VectorUpsertRequest(BaseModel):
    collection: str
    material_id: str
    vector: List[float]
    payload: VectorMetadata


class VectorUpsertResponse(BaseModel):
    material_id: str
    collection: str
    status: str


class BatchVectorUpsertRequest(BaseModel):
    collection: str
    vectors: List[VectorUpsertRequest]


class BatchVectorUpsertResponse(BaseModel):
    collection: str
    upserted: int
    failed: int
    details: Optional[List[Dict[str, Any]]] = None
