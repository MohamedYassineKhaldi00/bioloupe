import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worker.tasks.embedding_tasks import generate_material_embedding, batch_generate_embeddings


@pytest.mark.asyncio
async def test_generate_material_embedding_calls_services():
    db = AsyncMock()
    # fake material lookup
    fake_material = MagicMock()
    fake_material.id = 'mat-1'
    fake_material.title = 'Title'
    fake_material.metadata_ = {'abstract': 'abs'}

    async def fake_execute(sql, params=None):
        class R:
            def first(self):
                return fake_material
        return R()

    db.execute = AsyncMock(side_effect=fake_execute)
    db.commit = AsyncMock()

    vector_service = MagicMock()
    vector_service.upsert_vector = AsyncMock(return_value=True)

    res = await generate_material_embedding(db, vector_service, 'mat-1')
    assert res['material_id'] == 'mat-1'
    assert 'point_id' in res


@pytest.mark.asyncio
async def test_batch_generate_embeddings():
    db = AsyncMock()
    db.execute = AsyncMock()
    vector_service = MagicMock()
    vector_service.upsert_vector = AsyncMock(return_value=True)

    results = await batch_generate_embeddings(db, vector_service, ['m1', 'm2'])
    assert 'successes' in results
    assert isinstance(results['successes'], list)
