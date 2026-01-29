from __future__ import annotations

from pydantic import BaseModel


class PaperMetadata(BaseModel):
    doi: str | None = None
    authors: list[str] | None = None
    publication_date: str | None = None
    journal: str | None = None
    abstract: str | None = None
    keywords: list[str] | None = None


class SequenceMetadata(BaseModel):
    sequence_type: str | None = None
    sequence: str | None = None
    length: int | None = None
    organism: str | None = None
    uniprot_id: str | None = None
    gene_name: str | None = None


class ImageMetadata(BaseModel):
    image_type: str | None = None
    dimensions: dict[str, int] | None = None
    channels: list[str] | None = None
    magnification: str | None = None
    capture_date: str | None = None


class ExperimentMetadata(BaseModel):
    experiment_type: str | None = None
    conditions: dict | None = None
    outcomes: dict | None = None
    date_performed: str | None = None


class NoteMetadata(BaseModel):
    content: str | None = None
    mentions: list[str] | None = None
    linked_materials: list[str] | None = None
