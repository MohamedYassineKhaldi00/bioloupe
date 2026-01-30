from __future__ import annotations

import numpy as np
from typing import Iterable

from app.core.qdrant_config import get_all_collections
from app.core.vector_exceptions import VectorDimensionMismatch, CollectionNotFound


def _collection_map() -> dict[str, int]:
    return {c.name: c.vector_size for c in get_all_collections()}


def validate_vector_dimensions(collection: str, vector: Iterable[float]) -> None:
    """Raise VectorDimensionMismatch if vector does not match collection config."""
    mapping = _collection_map()
    if collection not in mapping:
        raise CollectionNotFound(collection)

    expected = mapping[collection]
    actual = len(vector) if not isinstance(vector, np.ndarray) else vector.shape[0]
    if actual != expected:
        raise VectorDimensionMismatch(collection, expected, actual)


def validate_payload_metadata(payload: dict) -> None:
    # Minimal payload validation: ensure required fields exist
    required = ("material_id", "session_id", "team_id", "modality")
    for key in required:
        if key not in payload:
            raise ValueError(f"Missing payload field: {key}")
