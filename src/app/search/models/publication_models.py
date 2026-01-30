from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, constr


class PublicationQuerySource(str, Enum):
    pubmed = "pubmed"
    arxiv = "arxiv"


class PublicationSearchRequest(BaseModel):
    query: constr(min_length=1)
    sources: List[PublicationQuerySource] = Field(
        default_factory=lambda: [PublicationQuerySource.pubmed, PublicationQuerySource.arxiv]
    )
    limit: int = Field(default=10, ge=1, le=50)
    page: int = Field(default=1, ge=1)


class PublicationSearchResult(BaseModel):
    title: str
    snippet: Optional[str] = None
    source: PublicationQuerySource
    publication_id: str
    score: float
    metadata: Dict[str, Any]
    similar_materials: List[Dict[str, Any]] = Field(default_factory=list)


class PublicationSearchResponse(BaseModel):
    query: str
    total: int
    results: List[PublicationSearchResult]


class SavePublicationSearchRequest(BaseModel):
    name: constr(min_length=3)
    query: constr(min_length=1)
    sources: List[PublicationQuerySource] = Field(
        default_factory=lambda: [PublicationQuerySource.pubmed, PublicationQuerySource.arxiv]
    )
    filters: Optional[Dict[str, Any]] = None
    notify_email: bool = False


class SavedPublicationSearchResponse(BaseModel):
    id: str
    name: str
    query: str
    sources: List[PublicationQuerySource]
    filters: Optional[Dict[str, Any]]
    notify_email: bool
    created_at: str
    updated_at: str


class SavedPublicationSearchListResponse(BaseModel):
    saved_searches: List[SavedPublicationSearchResponse]
