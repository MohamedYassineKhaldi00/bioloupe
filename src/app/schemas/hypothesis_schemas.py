"""
Schemas for AI-powered hypothesis generation.

Request/response models for hypothesis generation endpoints.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class HypothesisGenerationRequest(BaseModel):
    """Request model for hypothesis generation."""

    session_id: str = Field(
        ...,
        description="Session ID to analyze for hypothesis generation",
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
    )
    research_goal: str = Field(
        ...,
        description="Research goal or question to address",
        example="Improve protein-ligand binding affinity for drug discovery",
        min_length=10,
        max_length=1000,
    )
    num_hypotheses: int = Field(
        default=5,
        description="Number of hypotheses to generate",
        ge=1,
        le=20,
    )
    focus_area: Optional[str] = Field(
        default=None,
        description="Optional specific focus area (e.g., 'directed evolution', 'CRISPR editing')",
        example="directed evolution",
        max_length=200,
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="LiteLLM model name (e.g., gpt-4o, claude-3-5-sonnet, mistral-large, groq/llama-3.1-70b)",
        example="gpt-4o-mini",
    )


class HypothesisResponse(BaseModel):
    """Response model for a single hypothesis."""

    hypothesis: str = Field(
        ...,
        description="The hypothesis statement",
        example="Introducing specific mutations at the binding site will increase ligand affinity by 2-3 fold",
    )
    rationale: str = Field(
        ...,
        description="Scientific rationale explaining why this hypothesis is likely to work",
        example="Similar mutations in related proteins showed 2.5x affinity improvements in 15 peer-reviewed studies",
    )
    experimental_approach: str = Field(
        ...,
        description="Suggested experimental approach to test the hypothesis",
        example="1. Design site-directed mutagenesis primers\n2. Generate mutants\n3. Measure binding with SPR",
    )
    expected_outcomes: str = Field(
        ...,
        description="Predicted experimental outcomes",
        example="KD should decrease from 100nM to 30-50nM, measured by surface plasmon resonance",
    )
    required_resources: List[str] = Field(
        default_factory=list,
        description="List of required resources and reagents",
        example=["Site-directed mutagenesis kit", "SPR instrument", "Recombinant protein expression system"],
    )
    evidence_citations: List[str] = Field(
        default_factory=list,
        description="Supporting evidence from literature",
        example=["Smith et al. 2023 - Nature", "Jones et al. 2022 - Cell"],
    )
    feasibility_score: float = Field(
        ...,
        description="Feasibility score (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
        example=0.85,
    )
    evidence_score: float = Field(
        ...,
        description="Strength of supporting evidence (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
        example=0.92,
    )
    novelty_score: float = Field(
        ...,
        description="Novelty compared to existing work (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
        example=0.75,
    )
    overall_score: float = Field(
        ...,
        description="Overall score combining feasibility, evidence, and novelty (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
        example=0.84,
    )


class HypothesesListResponse(BaseModel):
    """Response model for list of generated hypotheses."""

    session_id: str = Field(..., description="Session ID")
    research_goal: str = Field(..., description="Research goal")
    hypotheses: List[HypothesisResponse] = Field(
        ...,
        description="List of generated hypotheses, ordered by overall_score descending",
    )
    model_used: str = Field(
        ...,
        description="LLM model used for generation",
        example="gpt-4o-mini",
    )
    evidence_count: int = Field(
        ...,
        description="Number of similar experiments used as evidence",
        example=47,
    )
    patterns_identified: int = Field(
        ...,
        description="Number of patterns extracted from evidence",
        example=8,
    )


class PatternResponse(BaseModel):
    """Response model for identified experimental pattern."""

    description: str = Field(..., description="Pattern description")
    methods: List[str] = Field(default_factory=list, description="Common methods")
    conditions: List[str] = Field(default_factory=list, description="Common conditions")
    success_factors: List[str] = Field(default_factory=list, description="Success factors")
    evidence_count: int = Field(..., description="Number of experiments supporting this pattern")
    confidence_score: float = Field(
        ...,
        description="Confidence in this pattern (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )


class EvidenceResponse(BaseModel):
    """Response model for evidence from similar experiments."""

    experiment_type: str = Field(..., description="Type of experiment", example="paper")
    experiment_id: str = Field(..., description="Experiment identifier")
    title: str = Field(..., description="Experiment title")
    similarity_score: float = Field(
        ...,
        description="Similarity score to session materials (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )
    abstract: Optional[str] = Field(None, description="Abstract or summary")
    key_findings: Optional[str] = Field(None, description="Key findings")
