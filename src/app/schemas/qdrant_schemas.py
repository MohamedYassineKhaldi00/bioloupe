from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UnifiedPayload(BaseModel):
    material_id: str
    session_id: str
    team_id: str
    modality: str
    title: str
    content_preview: str
    metadata: dict | None = None
    source: str = "internal"
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_model: str


class PublicationPayload(BaseModel):
    material_id: str
    session_id: str
    team_id: str
    title: str
    content_preview: str
    metadata: dict | None = None
    source: str = "internal"
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_model: str

    doi: str | None = None
    authors: list[str] | None = None
    journal: str | None = None
    citation_count: int | None = None
    publication_date: str | None = None


class SequencePayload(BaseModel):
    material_id: str
    session_id: str
    team_id: str
    title: str
    content_preview: str
    metadata: dict | None = None
    source: str = "internal"
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_model: str

    sequence_type: str | None = None
    length: int | None = None
    organism: str | None = None
    uniprot_id: str | None = None


class ExperimentPayload(BaseModel):
    material_id: str
    session_id: str
    team_id: str
    title: str
    content_preview: str
    metadata: dict | None = None
    source: str = "internal"
    indexed_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_model: str

    experiment_type: str | None = None
    conditions: dict | None = None
    outcomes: dict | None = None
    date_performed: str | None = None
