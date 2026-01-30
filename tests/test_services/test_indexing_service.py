import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.indexing_service import IndexingService
import uuid


@pytest.mark.asyncio
async def test_index_daily_publications_success():
    from unittest.mock import AsyncMock, MagicMock

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    vector_service = MagicMock()
    vector_service.upsert_vector = AsyncMock(return_value=True)

    pubmed_fetcher = MagicMock()
    pubmed_fetcher.search = AsyncMock(return_value=[
        {
            "source": "pubmed",
            "external_id": "123456",
            "title": "Test Paper",
            "abstract": "Test abstract",
            "authors": ["Author One"],
            "journal": "Test Journal",
            "publication_date": "2024-01-01",
            "doi": "10.1234/test"
        }
    ])

    arxiv_fetcher = MagicMock()
    arxiv_fetcher.search = AsyncMock(return_value=[])

    biorxiv_fetcher = MagicMock()
    biorxiv_fetcher.search = AsyncMock(return_value=[])

    service = IndexingService(
        db=db,
        vector_service=vector_service,
        pubmed_fetcher=pubmed_fetcher,
        arxiv_fetcher=arxiv_fetcher,
        biorxiv_fetcher=biorxiv_fetcher
    )

    stats = await service.index_daily_publications()

    assert stats["total_indexed"] == 1
    assert stats["sources_processed"] == 3
    assert len(stats["errors"]) == 0


@pytest.mark.asyncio
async def test_publication_deduplication():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = object()
    db.execute = AsyncMock(return_value=result)

    existing_material = SimpleNamespace(
        id=uuid.uuid4(),
        material_type="paper",
        title="Existing Paper",
        metadata_={"doi": "10.1234/test"},
        session_id=uuid.uuid4(),
        uploaded_by_id=None
    )
    db.add(existing_material)
    await db.commit()

    vector_service = MagicMock()
    pubmed_fetcher = MagicMock()
    arxiv_fetcher = MagicMock()
    biorxiv_fetcher = MagicMock()

    service = IndexingService(
        db=db,
        vector_service=vector_service,
        pubmed_fetcher=pubmed_fetcher,
        arxiv_fetcher=arxiv_fetcher,
        biorxiv_fetcher=biorxiv_fetcher
    )

    sample_publication = {
        "source": "pubmed",
        "external_id": "123456",
        "title": "CRISPR-Cas9 genome editing",
        "abstract": "This paper discusses CRISPR-Cas9...",
        "authors": ["John Smith", "Jane Doe"],
        "journal": "Nature",
        "publication_date": "2024-01-15",
        "doi": "10.1234/test"
    }

    exists = await service._publication_exists(sample_publication)

    assert exists is True


@pytest.mark.asyncio
async def test_create_material_from_publication():
    from unittest.mock import AsyncMock, MagicMock

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    vector_service = MagicMock()
    pubmed_fetcher = MagicMock()
    arxiv_fetcher = MagicMock()
    biorxiv_fetcher = MagicMock()

    service = IndexingService(
        db=db,
        vector_service=vector_service,
        pubmed_fetcher=pubmed_fetcher,
        arxiv_fetcher=arxiv_fetcher,
        biorxiv_fetcher=biorxiv_fetcher
    )

    sample_publication = {
        "source": "pubmed",
        "external_id": "123456",
        "title": "CRISPR-Cas9 genome editing",
        "abstract": "This paper discusses CRISPR-Cas9...",
        "authors": ["John Smith", "Jane Doe"],
        "journal": "Nature",
        "publication_date": "2024-01-15",
        "doi": "10.1234/test"
    }

    material = await service._create_material(sample_publication, "pubmed")

    assert material.title == "CRISPR-Cas9 genome editing"
    assert material.material_type == "paper"
    assert material.metadata_["doi"] == "10.1234/test"
    assert material.session_id is None
