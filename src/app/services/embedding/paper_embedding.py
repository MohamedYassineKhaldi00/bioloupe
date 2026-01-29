"""Paper embedding service using SPECTER2."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Optional

import numpy as np

from app.core.exceptions import EmbeddingError, InvalidPaperError
from app.core.ml_config import ModelConfig
from app.models.material import Material
from app.services.embedding.specter2_service import Specter2Service
from app.utils.pdf_parser import PDFParser, PaperSections
from app.utils.text_preprocessor import ScientificTextPreprocessor

logger = logging.getLogger(__name__)


class PaperEmbeddingService(Specter2Service):
    """SPECTER2-based service for paper embeddings."""

    def __init__(self, config: ModelConfig) -> None:
        """Initialize paper embedding service.

        Args:
            config: Model configuration
        """
        super().__init__(config)
        self._pdf_parser: Optional[PDFParser] = None
        self._text_preprocessor: Optional[ScientificTextPreprocessor] = None

    async def load_model(self) -> None:
        """Load model and initialize utilities."""
        await super().load_model()
        self._pdf_parser = PDFParser()
        self._text_preprocessor = ScientificTextPreprocessor(
            self._tokenizer
        )

    async def embed_paper(
        self,
        title: str,
        abstract: str,
        full_text: Optional[str] = None,
    ) -> np.ndarray:
        """Generate embedding for paper.

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Optional full text

        Returns:
            Embedding vector

        Raises:
            InvalidPaperError: If paper data invalid
            EmbeddingError: If embedding fails
        """
        self._validate_paper_input(title, abstract)

        if not self._is_loaded:
            await self.load_model()

        try:
            combined_text = self._prepare_paper_text(
                title, abstract, full_text
            )
            return await self.embed_with_cache(combined_text)

        except InvalidPaperError:
            raise
        except Exception as e:
            logger.error(f"Paper embedding failed: {e}")
            raise EmbeddingError(f"Failed to embed paper: {str(e)}")

    async def embed_from_pdf(self, pdf_path: str) -> np.ndarray:
        """Generate embedding from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Embedding vector

        Raises:
            InvalidPaperError: If PDF parsing fails
            EmbeddingError: If embedding fails
        """
        if not self._is_loaded:
            await self.load_model()

        try:
            sections = await self._extract_pdf_sections(pdf_path)

            if not sections.title and not sections.abstract:
                raise InvalidPaperError(
                    "Could not extract title or abstract from PDF"
                )

            return await self.embed_paper(
                title=sections.title,
                abstract=sections.abstract,
                full_text=sections.introduction,
            )

        except InvalidPaperError:
            raise
        except Exception as e:
            logger.error(f"PDF embedding failed: {e}")
            raise EmbeddingError(f"Failed to embed PDF: {str(e)}")

    async def embed_from_metadata(
        self, material: Material
    ) -> np.ndarray:
        """Generate embedding from Material metadata.

        Args:
            material: Material with metadata

        Returns:
            Embedding vector

        Raises:
            InvalidPaperError: If metadata invalid
            EmbeddingError: If embedding fails
        """
        if not material.title:
            raise InvalidPaperError("Material has no title")

        metadata = material.metadata_ or {}
        abstract = metadata.get("abstract", "")

        if not abstract:
            logger.warning(
                f"Material {material.id} has no abstract in metadata"
            )

        doi = metadata.get("doi", "")
        cache_key = self._generate_doi_cache_key(doi) if doi else None

        if cache_key:
            cached = await self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        try:
            embedding = await self.embed_paper(
                title=material.title, abstract=abstract
            )

            if cache_key:
                await self._save_to_cache(cache_key, embedding)

            return embedding

        except Exception as e:
            logger.error(f"Metadata embedding failed: {e}")
            raise EmbeddingError(
                f"Failed to embed from metadata: {str(e)}"
            )

    async def embed_papers_batch(
        self,
        papers: list[tuple[str, str, Optional[str]]],
        batch_size: int = 16,
    ) -> np.ndarray:
        """Generate embeddings for batch of papers.

        Args:
            papers: List of (title, abstract, full_text) tuples
            batch_size: Batch size

        Returns:
            Array of embeddings

        Raises:
            EmbeddingError: If batch embedding fails
        """
        if not self._is_loaded:
            await self.load_model()

        try:
            prepared_texts = [
                self._prepare_paper_text(title, abstract, full_text)
                for title, abstract, full_text in papers
            ]

            return await self.embed_batch(
                prepared_texts, batch_size=batch_size
            )

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise EmbeddingError(f"Failed to embed batch: {str(e)}")

    def _validate_paper_input(
        self, title: str, abstract: str
    ) -> None:
        """Validate paper input data.

        Args:
            title: Paper title
            abstract: Paper abstract

        Raises:
            InvalidPaperError: If validation fails
        """
        if not title or not title.strip():
            raise InvalidPaperError("Paper title is required")

        if not abstract or not abstract.strip():
            raise InvalidPaperError("Paper abstract is required")

    def _prepare_paper_text(
        self, title: str, abstract: str, full_text: Optional[str]
    ) -> str:
        """Prepare combined paper text for embedding.

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Optional full text

        Returns:
            Prepared text
        """
        return self._text_preprocessor.combine_paper_parts(
            title=title,
            abstract=abstract,
            introduction=full_text or "",
            max_tokens=self.config.max_sequence_length,
        )

    async def _extract_pdf_sections(
        self, pdf_path: str
    ) -> PaperSections:
        """Extract sections from PDF.

        Args:
            pdf_path: Path to PDF

        Returns:
            Parsed sections
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._extract_pdf_sync, pdf_path
        )

    def _extract_pdf_sync(self, pdf_path: str) -> PaperSections:
        """Extract PDF sections synchronously.

        Args:
            pdf_path: Path to PDF

        Returns:
            Parsed sections
        """
        text = self._pdf_parser.extract_text_from_pdf(pdf_path)
        return self._pdf_parser.parse_sections(text)

    def _generate_doi_cache_key(self, doi: str) -> str:
        """Generate cache key from DOI.

        Args:
            doi: Paper DOI

        Returns:
            Cache key
        """
        doi_hash = hashlib.sha256(doi.encode()).hexdigest()
        return f"embedding:paper:doi:{doi_hash}"

    def _generate_cache_key(self, input_data: Any) -> str:
        """Generate cache key for paper text.

        Args:
            input_data: Input text

        Returns:
            Cache key
        """
        if isinstance(input_data, str):
            text_hash = hashlib.sha256(input_data.encode()).hexdigest()
            return f"embedding:paper:text:{text_hash}"

        return super()._generate_cache_key(input_data)
