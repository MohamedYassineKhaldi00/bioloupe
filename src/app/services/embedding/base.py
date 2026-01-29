"""Base embedding service class."""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from app.core.exceptions import EmbeddingError
from app.core.ml_config import ModelConfig, get_ml_settings
from app.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding services."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize embedding service.

        Args:
            config: Model configuration
        """
        self.config = config
        self.settings = get_ml_settings()
        self._model: Any = None
        self._is_loaded = False

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self.config.name

    @property
    def model_cache_dir(self) -> str:
        """Get model cache directory."""
        return self.settings.ml_models_cache_dir

    @property
    def device(self) -> str:
        """Get device for model execution."""
        return self.config.device

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._is_loaded

    @abstractmethod
    async def load_model(self) -> None:
        """Load the embedding model.

        Raises:
            ModelLoadError: If model fails to load
        """
        pass

    @abstractmethod
    async def embed(self, input_data: Any) -> np.ndarray:
        """Generate embedding for single input.

        Args:
            input_data: Input data to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    @abstractmethod
    async def embed_batch(
        self, input_data: list[Any], batch_size: int | None = None
    ) -> np.ndarray:
        """Generate embeddings for batch of inputs.

        Args:
            input_data: List of inputs to embed
            batch_size: Batch size for processing

        Returns:
            Array of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    async def get_embedding_dim(self) -> int:
        """Get embedding dimension.

        Returns:
            Embedding dimension
        """
        return self.config.embedding_dim

    async def embed_with_cache(self, input_data: Any) -> np.ndarray:
        """Generate embedding with caching.

        Args:
            input_data: Input data to embed

        Returns:
            Embedding vector
        """
        if not self.settings.ml_enable_caching:
            return await self.embed(input_data)

        cache_key = self._generate_cache_key(input_data)
        cached = await self._get_from_cache(cache_key)

        if cached is not None:
            return cached

        embedding = await self.embed(input_data)
        await self._save_to_cache(cache_key, embedding)
        return embedding

    def _generate_cache_key(self, input_data: Any) -> str:
        """Generate cache key for input data.

        Args:
            input_data: Input data

        Returns:
            Cache key
        """
        data_str = json.dumps(input_data, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return f"embedding:{self.model_name}:{data_hash}"

    async def _get_from_cache(self, cache_key: str) -> np.ndarray | None:
        """Get embedding from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached embedding or None
        """
        try:
            redis_client = get_redis_client()
            cached_bytes = await redis_client.get(cache_key)

            if cached_bytes:
                return np.frombuffer(cached_bytes, dtype=np.float32)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None

    async def _save_to_cache(
        self, cache_key: str, embedding: np.ndarray
    ) -> None:
        """Save embedding to cache.

        Args:
            cache_key: Cache key
            embedding: Embedding to cache
        """
        try:
            redis_client = get_redis_client()
            embedding_bytes = embedding.astype(np.float32).tobytes()
            await redis_client.setex(
                cache_key,
                self.settings.ml_cache_ttl_seconds,
                embedding_bytes,
            )
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _validate_input(self, input_data: Any) -> None:
        """Validate input data.

        Args:
            input_data: Input data to validate

        Raises:
            EmbeddingError: If validation fails
        """
        if input_data is None:
            raise EmbeddingError("Input data cannot be None")

    def _validate_batch(self, input_data: list[Any]) -> None:
        """Validate batch input data.

        Args:
            input_data: Batch input data to validate

        Raises:
            EmbeddingError: If validation fails
        """
        if not isinstance(input_data, list):
            raise EmbeddingError("Batch input must be a list")

        if len(input_data) == 0:
            raise EmbeddingError("Batch input cannot be empty")
