"""Schemas for variant ranking requests and responses."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class SequenceVariant(BaseModel):
    """Sequence variant for ranking."""

    id: str | None = None
    sequence: str = Field(..., description="Amino acid or nucleotide sequence")
    name: str | None = None
    sequence_type: str = Field(default="protein", description="protein, dna, or rna")


class VariantRankingRequest(BaseModel):
    """Request to rank sequence variants."""

    sequences: list[dict[str, Any]] = Field(..., description="List of sequence variants")
    target_property: str = Field(..., description="Property to optimize for")
    max_variants_to_test: int = Field(default=10, ge=1, le=100)


class EvidenceItem(BaseModel):
    """Evidence supporting a variant ranking."""

    sequence_id: str
    similarity: float
    outcome_value: Any
    outcome_type: str
    source: str
    description: str


class RankedVariant(BaseModel):
    """Ranked sequence variant with success prediction."""

    sequence: dict[str, Any]
    success_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[EvidenceItem]
    recommended_priority: str
    explanation: str | None = None


class VariantRankingResponse(BaseModel):
    """Response containing ranked variants."""

    ranking_id: str
    ranked_variants: list[RankedVariant]
    recommended_for_testing: list[RankedVariant]
    summary: dict[str, int]


class RankingSummary(BaseModel):
    """Summary statistics for variant ranking."""

    total_variants: int
    high_priority: int
    medium_priority: int
    low_priority: int
