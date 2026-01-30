import pytest
import numpy as np

from app.utils.vector_validators import validate_vector_dimensions
from app.core.vector_exceptions import VectorDimensionMismatch, CollectionNotFound


def test_validate_vector_dimensions_success():
    v = np.zeros(768)
    # Should not raise
    validate_vector_dimensions("bioloupe_unified", v)


def test_validate_vector_dimensions_mismatch():
    v = np.zeros(10)
    with pytest.raises(VectorDimensionMismatch):
        validate_vector_dimensions("bioloupe_unified", v)


def test_validate_collection_not_found():
    v = np.zeros(10)
    with pytest.raises(CollectionNotFound):
        validate_vector_dimensions("nonexistent_collection", v)
