import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.external.pubmed_fetcher import PubMedFetcher
from datetime import datetime


@pytest.mark.asyncio
async def test_pubmed_search_success():
    fetcher = PubMedFetcher()

    with patch.object(fetcher, '_search_pmids', return_value=["123456"]):
        with patch.object(fetcher, '_fetch_details', return_value=[{
            "source": "pubmed",
            "external_id": "123456",
            "title": "Test Paper",
            "abstract": "Test abstract",
            "authors": ["Author One"],
            "journal": "Test Journal",
            "publication_date": "2024-01-01",
            "doi": "10.1234/test"
        }]):
            results = await fetcher.search(query="CRISPR", max_results=10)

            assert len(results) == 1
            assert results[0]["title"] == "Test Paper"
            assert results[0]["doi"] == "10.1234/test"


@pytest.mark.asyncio
async def test_pubmed_search_with_date_range():
    fetcher = PubMedFetcher()
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)

    with patch.object(fetcher, '_search_pmids', return_value=[]) as mock_search:
        await fetcher.search(
            query="biology",
            start_date=start_date,
            end_date=end_date
        )

        mock_search.assert_called_once()
        args = mock_search.call_args[0]
        assert args[1] == start_date
        assert args[2] == end_date


@pytest.mark.asyncio
async def test_pubmed_rate_limiting():
    fetcher = PubMedFetcher()

    import time
    start_time = time.time()

    with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = MagicMock(
            status_code=200,
            text='<PubmedArticleSet></PubmedArticleSet>',
            json=lambda: {"esearchresult": {"idlist": []}}
        )
        mock_request.return_value.raise_for_status = lambda: None

        await fetcher._rate_limited_request("GET", "http://test.com")
        await fetcher._rate_limited_request("GET", "http://test.com")

    elapsed = time.time() - start_time
    assert elapsed >= fetcher.rate_limit


@pytest.mark.asyncio
async def test_pubmed_retry_on_failure():
    fetcher = PubMedFetcher()

    with patch.object(fetcher.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            MagicMock(status_code=200, json=lambda: {})
        ]
        mock_request.return_value.raise_for_status = lambda: None

        await fetcher._rate_limited_request("GET", "http://test.com")

        assert mock_request.call_count == 3


@pytest.mark.asyncio
async def test_parse_pubmed_xml():
    fetcher = PubMedFetcher()

    xml_sample = '''<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>123456</PMID>
                <Article>
                    <ArticleTitle>Test Title</ArticleTitle>
                    <Abstract>
                        <AbstractText>Test abstract text</AbstractText>
                    </Abstract>
                    <AuthorList>
                        <Author>
                            <LastName>Smith</LastName>
                            <ForeName>John</ForeName>
                        </Author>
                    </AuthorList>
                    <Journal>
                        <Title>Test Journal</Title>
                    </Journal>
                    <ELocationID EIdType="doi">10.1234/test</ELocationID>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>'''

    results = fetcher._parse_pubmed_xml(xml_sample)

    assert len(results) == 1
    assert results[0]["title"] == "Test Title"
    assert results[0]["abstract"] == "Test abstract text"
    assert results[0]["authors"] == ["John Smith"]
    assert results[0]["doi"] == "10.1234/test"
