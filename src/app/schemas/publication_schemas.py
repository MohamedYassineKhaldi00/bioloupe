from __future__ import annotations

from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


class PublicationMetadata(BaseModel):
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    journal: Optional[str] = None
    authors: Optional[List[str]] = None
    publication_date: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None


class Publication(BaseModel):
    source: str
    external_id: str
    title: str
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    metadata: Optional[PublicationMetadata] = None


class FetchRequest(BaseModel):
    query: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_results: int = 100


class FetchResponse(BaseModel):
    publications: List[Publication]
    total: int
    next_page_token: Optional[str] = None
