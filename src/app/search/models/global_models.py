from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, constr


class GlobalSearchEntity(str, Enum):
    user = "user"
    team = "team"
    session = "session"
    material = "material"


class DateRange(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class FacetFilter(BaseModel):
    team_id: Optional[UUID] = None
    material_type: Optional[str] = None
    modality: Optional[str] = None
    tags: Optional[List[str]] = None
    date_range: Optional[DateRange] = None


class GlobalSearchRequest(BaseModel):
    query: constr(min_length=1)
    entities: List[GlobalSearchEntity] = Field(
        default_factory=lambda: [entity for entity in GlobalSearchEntity]
    )
    filters: Optional[FacetFilter] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class GlobalSearchResult(BaseModel):
    entity_type: GlobalSearchEntity
    id: str
    title: str
    description: Optional[str]
    team_id: Optional[str]
    score: float
    metadata: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None


class GlobalSearchResponse(BaseModel):
    results: List[GlobalSearchResult]
    total: int
    facets: Dict[str, Dict[str, int]]
    elapsed_ms: int


class AutocompleteResponse(BaseModel):
    suggestions: List[str]
