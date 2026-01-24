from __future__ import annotations

import logging
from qdrant_client.http import models as rest

from ...app.core.qdrant_config import (
    EXPERIMENTS_COLLECTION,
    PUBLICATIONS_COLLECTION,
    SEQUENCES_COLLECTION,
    UNIFIED_COLLECTION,
    get_all_collections,
)
from ...app.db.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)


async def init_qdrant() -> None:
    wrapper = get_qdrant_client()
    for config in get_all_collections():
        exists = await wrapper.with_retry(
            wrapper.client.collection_exists,
            collection_name=config.name,
        )
        if not exists:
            await wrapper.with_retry(
                wrapper.client.create_collection,
                collection_name=config.name,
                vectors_config=rest.VectorParams(
                    size=config.vector_size,
                    distance=config.distance,
                ),
            )

    await _ensure_payload_indexes(wrapper)


async def _ensure_payload_indexes(wrapper) -> None:
    async def create_index(collection: str, field: str, schema: rest.PayloadSchemaType) -> None:
        try:
            await wrapper.with_retry(
                wrapper.client.create_payload_index,
                collection_name=collection,
                field_name=field,
                field_schema=schema,
            )
        except Exception:
            return

    unified_fields = [
        "material_id",
        "session_id",
        "team_id",
        "modality",
        "source",
        "embedding_model",
    ]
    for field in unified_fields:
        await create_index(UNIFIED_COLLECTION.name, field, rest.PayloadSchemaType.KEYWORD)

    publication_fields = ["material_id", "session_id", "team_id", "doi", "journal"]
    for field in publication_fields:
        await create_index(PUBLICATIONS_COLLECTION.name, field, rest.PayloadSchemaType.KEYWORD)

    sequence_fields = ["material_id", "session_id", "team_id", "sequence_type", "organism", "uniprot_id"]
    for field in sequence_fields:
        await create_index(SEQUENCES_COLLECTION.name, field, rest.PayloadSchemaType.KEYWORD)

    experiment_fields = ["material_id", "session_id", "team_id", "experiment_type", "date_performed"]
    for field in experiment_fields:
        await create_index(EXPERIMENTS_COLLECTION.name, field, rest.PayloadSchemaType.KEYWORD)

    logger.info("Qdrant payload indexes ensured")
