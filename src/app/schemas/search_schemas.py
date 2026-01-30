from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SearchRequest(BaseModel):
    collection: str
    query_vector: List[float]
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20


class SearchResult(BaseModel):
    material_id: Optional[str]
    score: float
    modality: Optional[str]
    title: Optional[str]
    content_preview: Optional[str]
    metadata: Optional[Dict[str, Any]]
    session_id: Optional[str]
    indexed_at: Optional[str]
    explanation: Optional[Dict[str, Any]]


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    search_time_ms: int
