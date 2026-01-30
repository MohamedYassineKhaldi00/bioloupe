from __future__ import annotations

import logging
from app.worker.celery_app import get_task_decorator
from app.services.embedding_worker_service import EmbeddingWorkerService

logger = logging.getLogger(__name__)

_task = get_task_decorator()


@_task()
async def generate_material_embedding(db, vector_service, material_id: str):
    svc = EmbeddingWorkerService(db=db, vector_service=vector_service)
    return await svc.generate_material_embedding(material_id)


@_task()
async def batch_generate_embeddings(db, vector_service, material_ids: list):
    successes = []
    failures = []
    for mid in material_ids:
        try:
            res = await generate_material_embedding(db, vector_service, mid)
            successes.append(res)
        except Exception as e:
            failures.append({"material_id": mid, "error": str(e)})
    return {"successes": successes, "failures": failures}
