"""Multi-modal embedding fusion strategies."""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)

FusionMethod = Literal["concat", "average", "weighted_average"]


class EmbeddingFusion:
    """Fuses embeddings from multiple modalities."""

    def __init__(
        self,
        default_weights: dict[str, float] | None = None
    ) -> None:
        """Initialize fusion service.

        Args:
            default_weights: Default weights for weighted_average method
        """
        self._default_weights = default_weights or {
            "text": 0.6,
            "image": 0.4,
            "sequence": 0.5,
        }

    def fuse(
        self,
        embeddings: dict[str, np.ndarray],
        method: FusionMethod = "concat",
        weights: dict[str, float] | None = None,
    ) -> np.ndarray:
        """Fuse multiple embeddings.

        Args:
            embeddings: Dict mapping modality names to embeddings
            method: Fusion method (concat, average, weighted_average)
            weights: Custom weights for weighted_average (overrides defaults)

        Returns:
            Fused embedding vector

        Raises:
            ValueError: If embeddings dict empty or method invalid
        """
        if not embeddings:
            raise ValueError("Embeddings dict cannot be empty")

        if len(embeddings) == 1:
            return next(iter(embeddings.values()))

        if method == "concat":
            return self._concatenate(embeddings)
        elif method == "average":
            return self._average(embeddings)
        elif method == "weighted_average":
            fusion_weights = weights or self._default_weights
            return self._weighted_average(embeddings, fusion_weights)
        else:
            raise ValueError(f"Unknown fusion method: {method}")

    def _concatenate(
        self,
        embeddings: dict[str, np.ndarray]
    ) -> np.ndarray:
        """Concatenate embeddings.

        Args:
            embeddings: Dict of embeddings

        Returns:
            Concatenated embedding
        """
        sorted_keys = sorted(embeddings.keys())
        vectors = [embeddings[k] for k in sorted_keys]
        return np.concatenate(vectors)

    def _average(
        self,
        embeddings: dict[str, np.ndarray]
    ) -> np.ndarray:
        """Average embeddings.

        Args:
            embeddings: Dict of embeddings

        Returns:
            Averaged embedding

        Raises:
            ValueError: If dimensions don't match
        """
        vectors = list(embeddings.values())
        dims = [v.shape[0] for v in vectors]

        if len(set(dims)) > 1:
            raise ValueError(
                f"Cannot average embeddings with different dimensions: {dims}"
            )

        return np.mean(vectors, axis=0)

    def _weighted_average(
        self,
        embeddings: dict[str, np.ndarray],
        weights: dict[str, float],
    ) -> np.ndarray:
        """Weighted average of embeddings.

        Args:
            embeddings: Dict of embeddings
            weights: Dict of weights per modality

        Returns:
            Weighted average embedding

        Raises:
            ValueError: If dimensions don't match or weights missing
        """
        vectors = list(embeddings.values())
        dims = [v.shape[0] for v in vectors]

        if len(set(dims)) > 1:
            raise ValueError(
                f"Cannot average embeddings with different dimensions: {dims}"
            )

        modality_weights = []
        for modality in embeddings.keys():
            if modality not in weights:
                logger.warning(
                    f"Weight for modality '{modality}' not found, using 1.0"
                )
                modality_weights.append(1.0)
            else:
                modality_weights.append(weights[modality])

        weight_array = np.array(modality_weights)
        normalized_weights = weight_array / weight_array.sum()

        weighted_vectors = [
            emb * w
            for emb, w in zip(vectors, normalized_weights)
        ]

        return np.sum(weighted_vectors, axis=0)

    def update_default_weights(
        self,
        weights: dict[str, float]
    ) -> None:
        """Update default weights.

        Args:
            weights: New default weights
        """
        self._default_weights.update(weights)

    def get_fused_dimension(
        self,
        embeddings: dict[str, np.ndarray],
        method: FusionMethod,
    ) -> int:
        """Get dimension of fused embedding.

        Args:
            embeddings: Dict of embeddings
            method: Fusion method

        Returns:
            Dimension of fused embedding
        """
        if not embeddings:
            raise ValueError("Embeddings dict cannot be empty")

        dims = [v.shape[0] for v in embeddings.values()]

        if method == "concat":
            return sum(dims)
        elif method in ("average", "weighted_average"):
            if len(set(dims)) > 1:
                raise ValueError(
                    f"Cannot compute dimension for averaging with mismatched dims: {dims}"
                )
            return dims[0]
        else:
            raise ValueError(f"Unknown fusion method: {method}")
