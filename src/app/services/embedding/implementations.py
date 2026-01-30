"""Embedding service implementations for different models."""

from __future__ import annotations

from typing import Type

from app.services.embedding.base import BaseEmbeddingService


def get_embedding_service_class(model_name: str) -> Type[BaseEmbeddingService]:
    """Get embedding service class for a model.

    Args:
        model_name: Name of the model

    Returns:
        Embedding service class

    Raises:
        ValueError: If model not supported
    """
    # Import implementations lazily to avoid loading heavy dependencies
    if model_name == "specter2":
        from app.services.embedding.specter2_service import Specter2Service
        return Specter2Service

    if model_name == "paper_embedding":
        from app.services.embedding.paper_embedding import PaperEmbeddingService
        return PaperEmbeddingService

    if model_name == "esm2":
        from app.services.embedding.esm2_service import ESM2Service
        return ESM2Service

    if model_name == "clip":
        from app.services.embedding.clip_service import CLIPService
        return CLIPService

    raise ValueError(f"Unsupported model: {model_name}")


__all__ = ["get_embedding_service_class"]
