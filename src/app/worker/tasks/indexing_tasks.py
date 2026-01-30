from __future__ import annotations

import logging
from typing import Optional, List, Any
from datetime import datetime
from app.worker.celery_app import get_task_decorator
from app.services.indexing_service import IndexingService

logger = logging.getLogger(__name__)
_task = get_task_decorator()


@_task()
async def daily_publication_indexing(indexing_service: Optional[Any] = None) -> dict:
    """Run daily indexing job. If an IndexingService is provided (for tests), use it; otherwise construct one externally and pass it in."""
    try:
        if indexing_service is None:
            raise ValueError("IndexingService instance required")

        stats = await indexing_service.index_daily_publications()
        return stats
    except Exception as e:
        logger.exception("daily_publication_indexing failed: %s", e)
        raise


@_task()
async def index_source_publications(source: str, indexing_service: Optional[Any] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
    try:
        if indexing_service is None:
            raise ValueError("IndexingService instance required")

        fetcher = indexing_service.fetchers.get(source)
        if not fetcher:
            raise ValueError(f"Unknown source: {source}")

        pubs = await fetcher.search(query="biology OR biotechnology", start_date=start_date, end_date=end_date, max_results=500)
        count = await indexing_service._process_publications(pubs, source)
        return {"indexed": count}
    except Exception as e:
        logger.exception("index_source_publications failed: %s", e)
        raise


@_task()
async def index_topic_subscriptions(subscriptions: Optional[List[dict]] = None, indexing_service: Optional[Any] = None) -> dict:
    try:
        if indexing_service is None:
            raise ValueError("IndexingService instance required")

        total_indexed = 0
        if subscriptions is None:
            # In production, fetch subscriptions from DB; here we require them to be provided for deterministic behavior
            raise ValueError("subscriptions required")

        for sub in subscriptions:
            query = sub.get("keywords") or sub.get("topic")
            pubs = await indexing_service.fetchers["pubmed"].search(query=query, max_results=100)
            total_indexed += await indexing_service._process_publications(pubs, "pubmed")

        return {"total_indexed": total_indexed}
    except Exception as e:
        logger.exception("index_topic_subscriptions failed: %s", e)
        raise


@_task()
async def process_single_publication(publication: dict, indexing_service: Optional[Any] = None) -> dict:
    try:
        if indexing_service is None:
            raise ValueError("IndexingService instance required")

        count = await indexing_service._process_publications([publication], publication.get("source", "pubmed"))
        return {"indexed": count}
    except Exception as e:
        logger.exception("process_single_publication failed: %s", e)
        raise


@_task()
async def reindex_publications(publication_ids: Optional[List[str]] = None, date_range: Optional[dict] = None, indexing_service: Optional[Any] = None) -> dict:
    try:
        if indexing_service is None:
            raise ValueError("IndexingService instance required")

        # Minimal placeholder: in production, re-fetch metadata and re-run _process_publications
        reindexed = 0
        if publication_ids:
            for pid in publication_ids:
                # Here, the service would fetch publication details and reprocess
                reindexed += 1
        return {"reindexed": reindexed}
    except Exception as e:
        logger.exception("reindex_publications failed: %s", e)
        raise
