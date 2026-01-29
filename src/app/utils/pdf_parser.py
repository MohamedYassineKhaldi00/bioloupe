"""PDF text extraction and parsing utilities."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PaperSections:
    """Extracted sections from a scientific paper."""

    title: str
    abstract: str
    introduction: str
    body: str
    references: str


class PDFParser:
    """Extract and parse text from scientific papers."""

    SECTION_PATTERNS = {
        "abstract": re.compile(
            r"(?i)abstract[:\s]*(.*?)(?=\n\n|\nintroduction|\nkeywords)",
            re.DOTALL,
        ),
        "introduction": re.compile(
            r"(?i)(?:^|\n)introduction[:\s]*(.*?)(?=\n(?:[2-9]\.?|\n[A-Z]))",
            re.DOTALL,
        ),
        "methods": re.compile(
            r"(?i)(?:^|\n)(?:methods|materials and methods)[:\s]*(.*?)"
            r"(?=\n(?:[3-9]\.?|\n[A-Z]))",
            re.DOTALL,
        ),
        "results": re.compile(
            r"(?i)(?:^|\n)results[:\s]*(.*?)(?=\n(?:[4-9]\.?|\n[A-Z]))",
            re.DOTALL,
        ),
        "references": re.compile(
            r"(?i)(?:^|\n)references[:\s]*(.*?)$", re.DOTALL
        ),
    }

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract raw text from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text

        Raises:
            FileNotFoundError: If PDF not found
            ValueError: If text extraction fails
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            import fitz

            doc = fitz.open(pdf_path)
            text = self._extract_with_pymupdf(doc)
            doc.close()

            if not text.strip():
                logger.warning("Empty text, attempting OCR fallback")
                text = self._extract_with_ocr(pdf_path)

            return text

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise ValueError(f"Failed to extract text: {e}")

    def _extract_with_pymupdf(self, doc: "fitz.Document") -> str:
        """Extract text using PyMuPDF.

        Args:
            doc: Opened PDF document

        Returns:
            Extracted text
        """
        text_parts = []

        for page in doc:
            text_parts.append(page.get_text())

        return "\n".join(text_parts)

    def _extract_with_ocr(self, pdf_path: str) -> str:
        """Extract text using OCR fallback.

        Args:
            pdf_path: Path to PDF file

        Returns:
            OCR extracted text
        """
        try:
            import fitz
            from PIL import Image
            import pytesseract
            import io

            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(min(5, len(doc))):
                page = doc[page_num]
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes()))
                text = pytesseract.image_to_string(img)
                text_parts.append(text)

            doc.close()
            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def parse_sections(self, text: str) -> PaperSections:
        """Parse text into paper sections.

        Args:
            text: Raw paper text

        Returns:
            Parsed paper sections
        """
        title = self._extract_title(text)
        abstract = self._extract_section("abstract", text)
        introduction = self._extract_section("introduction", text)
        references = self._extract_section("references", text)

        body = self._extract_body(text, references)

        return PaperSections(
            title=title,
            abstract=abstract,
            introduction=introduction,
            body=body,
            references=references,
        )

    def _extract_title(self, text: str) -> str:
        """Extract title from paper.

        Args:
            text: Paper text

        Returns:
            Extracted title
        """
        lines = text.split("\n")
        non_empty = [line.strip() for line in lines if line.strip()]

        if not non_empty:
            return ""

        title_lines = []
        for line in non_empty[:5]:
            if len(line) < 150 and not line.lower().startswith(
                ("abstract", "keywords")
            ):
                title_lines.append(line)
            else:
                break

        return " ".join(title_lines)

    def _extract_section(self, section_name: str, text: str) -> str:
        """Extract specific section from text.

        Args:
            section_name: Name of section
            text: Paper text

        Returns:
            Section text
        """
        pattern = self.SECTION_PATTERNS.get(section_name)
        if not pattern:
            return ""

        match = pattern.search(text)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_body(self, text: str, references: str) -> str:
        """Extract main body text.

        Args:
            text: Full paper text
            references: References section

        Returns:
            Body text
        """
        if references:
            text = text.split(references)[0]

        abstract_match = self.SECTION_PATTERNS["abstract"].search(text)
        if abstract_match:
            text = text[abstract_match.end() :]

        return text.strip()
