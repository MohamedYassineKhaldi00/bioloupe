"""ESM-2 embedding service for protein sequences."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np

from app.core.exceptions import EmbeddingError, ModelLoadError
from app.core.ml_config import ModelConfig
from app.services.embedding.base import BaseEmbeddingService

logger = logging.getLogger(__name__)


class ESM2Service(BaseEmbeddingService):
    """ESM-2 embedding service for protein sequences."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize ESM-2 service.

        Args:
            config: Model configuration
        """
        super().__init__(config)
        self._tokenizer: Any = None

    async def load_model(self) -> None:
        """Load ESM-2 model and tokenizer.

        Raises:
            ModelLoadError: If model fails to load
        """
        try:
            logger.info(f"Loading ESM-2 from {self.config.model_path}")

            loop = asyncio.get_event_loop()
            self._model, self._tokenizer = await loop.run_in_executor(
                None, self._load_model_sync
            )

            self._is_loaded = True
            logger.info("ESM-2 loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load ESM-2: {e}")
            raise ModelLoadError(f"Failed to load ESM-2: {str(e)}")

    def _load_model_sync(self) -> tuple[Any, Any]:
        """Load model synchronously.

        Returns:
            Tuple of (model, tokenizer)
        """
        from transformers import AutoModel, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_path,
            cache_dir=self.model_cache_dir,
        )

        model = AutoModel.from_pretrained(
            self.config.model_path,
            cache_dir=self.model_cache_dir,
        )

        model.to(self.device)
        model.eval()

        return model, tokenizer

    async def embed(self, input_data: Any) -> np.ndarray:
        """Generate embedding for a protein sequence.

        Args:
            input_data: Protein sequence string

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
            logger.error(f"ESM-2 embedding failed: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    def _embed_sync(self, sequence: str) -> np.ndarray:
        """Generate embedding synchronously.

        Args:
            sequence: Protein sequence

        Returns:
            Embedding vector
        """
        import torch

        inputs = self._tokenizer(
            sequence,
            padding=True,
            truncation=True,
            max_length=self.config.max_sequence_length,
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()

        return embedding[0]

    async def embed_batch(
        self, input_data: list[Any], batch_size: int | None = None
    ) -> np.ndarray:
        """Generate embeddings for batch of sequences.

        Args:
            input_data: List of protein sequences
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
            logger.error(f"ESM-2 batch embedding failed: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}")

    def _embed_batch_sync(
        self, sequences: list[str], batch_size: int
    ) -> np.ndarray:
        """Generate embeddings synchronously in batches.

        Args:
            sequences: List of protein sequences
            batch_size: Batch size

        Returns:
            Array of embeddings
        """
        import torch

        embeddings = []

        for i in range(0, len(sequences), batch_size):
            batch = sequences[i : i + batch_size]

            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.config.max_sequence_length,
                return_tensors="pt",
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                batch_embeddings = (
                    outputs.last_hidden_state.mean(dim=1).cpu().numpy()
                )

            embeddings.append(batch_embeddings)

        return np.vstack(embeddings)
