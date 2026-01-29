"""Embedding services for BioLoupe."""

from app.services.embedding.base import BaseEmbeddingService
from app.services.embedding.model_loader import ModelLoader, get_model_loader
from app.services.embedding.paper_embedding import PaperEmbeddingService
from app.services.embedding.sequence_embedding import SequenceEmbeddingService
from app.services.embedding.image_embedding import ImageEmbeddingService
from app.services.embedding.unified_embedding import UnifiedEmbeddingService
from app.services.embedding.fusion import EmbeddingFusion
from app.services.embedding.storage import EmbeddingStorageService

__all__ = [
    "BaseEmbeddingService",
    "ModelLoader",
    "get_model_loader",
    "PaperEmbeddingService",
    "SequenceEmbeddingService",
    "ImageEmbeddingService",
    "UnifiedEmbeddingService",
    "EmbeddingFusion",
    "EmbeddingStorageService",
]
