import pytest
from unittest.mock import patch, MagicMock
from app.services.pdf_extraction_service import PDFExtractionService


@pytest.mark.asyncio
async def test_extract_from_bytes():
    service = PDFExtractionService()

    sample_pdf = b"%PDF-1.4\n..."

    with patch.object(service, '_extract_with_pdfplumber', return_value="Sample text"):
        with patch.object(service, '_segment_sections', return_value={"abstract": "Test"}):
            result = await service.extract_from_bytes(sample_pdf)

            assert result is not None
            assert "full_text" in result
            assert "sections" in result


@pytest.mark.asyncio
async def test_segment_sections():
    service = PDFExtractionService()

    text = """
    ABSTRACT
    This is the abstract section.

    INTRODUCTION
    This is the introduction section.

    METHODS
    This is the methods section.

    RESULTS
    This is the results section.
    """

    sections = service._segment_sections(text)

    assert "abstract" in sections
    assert "introduction" in sections
    assert "methods" in sections
    assert "results" in sections
    assert "abstract section" in sections["abstract"]


@pytest.mark.asyncio
async def test_download_pdf():
    service = PDFExtractionService()

    from unittest.mock import AsyncMock

    with patch.object(service.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.content = b"PDF content"
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        content = await service._download_pdf("http://example.com/paper.pdf")

        assert content == b"PDF content"
        mock_get.assert_called_once_with("http://example.com/paper.pdf")
