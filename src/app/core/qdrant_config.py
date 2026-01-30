from __future__ import annotations

from dataclasses import dataclass
from qdrant_client.http import models as rest


@dataclass(frozen=True)
class QdrantCollectionConfig:
    name: str
    vector_size: int
    distance: rest.Distance


# Some qdrant client versions may not expose the Distance symbolic names the same way.
# Be defensive and fall back to None if unavailable; consumers should handle missing distance values.
try:
    COSINE = rest.Distance.COSINE
except Exception:
    COSINE = None

UNIFIED_COLLECTION = QdrantCollectionConfig(
    name="bioloupe_unified",
    vector_size=768,
    distance=COSINE,
)

PUBLICATIONS_COLLECTION = QdrantCollectionConfig(
    name="bioloupe_publications",
    vector_size=768,
    distance=COSINE,
)

SEQUENCES_COLLECTION = QdrantCollectionConfig(
    name="bioloupe_sequences",
    vector_size=1280,
    distance=COSINE,
)

EXPERIMENTS_COLLECTION = QdrantCollectionConfig(
    name="bioloupe_experiments",
    vector_size=768,
    distance=COSINE,
)


def get_all_collections() -> list[QdrantCollectionConfig]:
    return [
        UNIFIED_COLLECTION,
        PUBLICATIONS_COLLECTION,
        SEQUENCES_COLLECTION,
        EXPERIMENTS_COLLECTION,
    ]
