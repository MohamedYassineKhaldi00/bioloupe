"""CLIP embedding service for images."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np

from app.core.exceptions import EmbeddingError, ModelLoadError
from app.core.ml_config import ModelConfig
from app.services.embedding.base import BaseEmbeddingService

logger = logging.getLogger(__name__)


class CLIPService(BaseEmbeddingService):
    """CLIP embedding service for images and text."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize CLIP service.

        Args:
            config: Model configuration
        """
        super().__init__(config)
        self._processor: Any = None

    async def load_model(self) -> None:
        """Load CLIP model and processor.

        Raises:
            ModelLoadError: If model fails to load
        """
        try:
            logger.info(f"Loading CLIP from {self.config.model_path}")

            loop = asyncio.get_event_loop()
            self._model, self._processor = await loop.run_in_executor(
                None, self._load_model_sync
            )

            self._is_loaded = True
            logger.info("CLIP loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}")
            raise ModelLoadError(f"Failed to load CLIP: {str(e)}")

    def _load_model_sync(self) -> tuple[Any, Any]:
        """Load model synchronously.

        Returns:
            Tuple of (model, processor)
        """
        from transformers import CLIPModel, CLIPProcessor

        processor = CLIPProcessor.from_pretrained(
            self.config.model_path,
            cache_dir=self.model_cache_dir,
        )

        model = CLIPModel.from_pretrained(
            self.config.model_path,
            cache_dir=self.model_cache_dir,
        )

        model.to(self.device)
        model.eval()

        return model, processor

    async def embed(self, input_data: Any) -> np.ndarray:
        """Generate embedding for an image or text.

        Args:
            input_data: PIL Image or text string

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        self._validate_input(input_data)

        if not self._is_loaded:
            await self.load_model()

        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self._embed_sync, input_data
            )
            return embedding

        except Exception as e:
            logger.error(f"CLIP embedding failed: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    def _embed_sync(self, input_data: Any) -> np.ndarray:
        """Generate embedding synchronously.

        Args:
            input_data: Image or text

        Returns:
            Embedding vector
        """
        import torch

        if isinstance(input_data, str):
            inputs = self._processor(
                text=[input_data],
                return_tensors="pt",
                padding=True,
                truncation=True,
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                embedding = self._model.get_text_features(**inputs).cpu().numpy()
        else:
            inputs = self._processor(
                images=input_data,
                return_tensors="pt",
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                embedding = self._model.get_image_features(**inputs).cpu().numpy()

        return embedding[0]

    async def embed_batch(
        self, input_data: list[Any], batch_size: int | None = None
    ) -> np.ndarray:
        """Generate embeddings for batch of images or texts.

        Args:
            input_data: List of images or texts
            batch_size: Batch size for processing

        Returns:
            Array of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        self._validate_batch(input_data)

        if not self._is_loaded:
            await self.load_model()

        batch_size = batch_size or self.config.batch_size

        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, self._embed_batch_sync, input_data, batch_size
            )
            return embeddings

        except Exception as e:
            logger.error(f"CLIP batch embedding failed: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}")

    def _embed_batch_sync(
        self, input_data: list[Any], batch_size: int
    ) -> np.ndarray:
        """Generate embeddings synchronously in batches.

        Args:
            input_data: List of inputs
            batch_size: Batch size

        Returns:
            Array of embeddings
        """
        import torch

        embeddings = []
        is_text = isinstance(input_data[0], str)

        for i in range(0, len(input_data), batch_size):
            batch = input_data[i : i + batch_size]

            if is_text:
                inputs = self._processor(
                    text=batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                )

                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                with torch.no_grad():
                    batch_embeddings = (
                        self._model.get_text_features(**inputs).cpu().numpy()
                    )
            else:
                inputs = self._processor(
                    images=batch,
                    return_tensors="pt",
                )

                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                with torch.no_grad():
                    batch_embeddings = (
                        self._model.get_image_features(**inputs).cpu().numpy()
                    )

            embeddings.append(batch_embeddings)

        return np.vstack(embeddings)
