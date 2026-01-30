import pytest
from unittest.mock import AsyncMock, MagicMock
from app.worker.tasks.indexing_tasks import (
    daily_publication_indexing,
    index_source_publications,
    index_topic_subscriptions,
    process_single_publication,
    reindex_publications,
)


@pytest.mark.asyncio
async def test_daily_publication_indexing_calls_service():
    svc = MagicMock()
    svc.index_daily_publications = AsyncMock(return_value={"total_indexed": 5})

    res = await daily_publication_indexing(svc)
    assert res["total_indexed"] == 5


@pytest.mark.asyncio
async def test_index_source_publications_calls_fetcher_and_process():
    svc = MagicMock()
    fake_fetcher = MagicMock()
    fake_fetcher.search = AsyncMock(return_value=[{"title": "p1"}])
    svc.fetchers = {"pubmed": fake_fetcher}
    svc._process_publications = AsyncMock(return_value=1)

    res = await index_source_publications("pubmed", indexing_service=svc)
    assert res["indexed"] == 1


@pytest.mark.asyncio
async def test_index_topic_subscriptions_requires_subscriptions():
    svc = MagicMock()
    with pytest.raises(ValueError):
        await index_topic_subscriptions(None, indexing_service=svc)


@pytest.mark.asyncio
async def test_process_single_publication_calls_process():
    svc = MagicMock()
    svc._process_publications = AsyncMock(return_value=1)
    pub = {"source": "pubmed", "title": "t"}

    res = await process_single_publication(pub, indexing_service=svc)
    assert res["indexed"] == 1


@pytest.mark.asyncio
async def test_reindex_publications_counts_ids():
    svc = MagicMock()
    res = await reindex_publications(publication_ids=["a", "b"], indexing_service=svc)
    assert res["reindexed"] == 2
