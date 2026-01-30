from __future__ import annotations

from typing import Dict, Any, Optional
import httpx
import tempfile
import os
import asyncio

import logging
logger = logging.getLogger(__name__)


class PDFExtractionService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60)

    async def extract_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            pdf_content = await self._download_pdf(url)
            return await self.extract_from_bytes(pdf_content)
        except Exception as e:
            logger.error(f"PDF extraction from URL failed: {e}")
            return None

    async def _download_pdf(self, url: str) -> bytes:
        response = await self.client.get(url)
        response.raise_for_status()
        return response.content

    async def extract_from_bytes(self, pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            text = await asyncio.get_event_loop().run_in_executor(None, self._extract_with_pdfplumber, tmp_path)

            if not text:
                text = await asyncio.get_event_loop().run_in_executor(None, self._extract_with_pypdf2, tmp_path)

            sections = self._segment_sections(text or "")

            return {
                "full_text": text or "",
                "sections": sections,
                "extraction_method": "pdfplumber"
            }

        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        try:
            import pdfplumber
        except Exception:
            logger.warning("pdfplumber not available, falling back to PyPDF2")
            return self._extract_with_pypdf2(pdf_path)

        text_parts = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text_parts.append(page.extract_text() or "")
        except Exception:
            return self._extract_with_pypdf2(pdf_path)

        return "\n\n".join(text_parts)

    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        try:
            from PyPDF2 import PdfReader
        except Exception:
            logger.error("PyPDF2 not available for PDF extraction")
            return ""

        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                tm = page.extract_text()
                text_parts.append(tm or "")

        return "\n\n".join(text_parts)

    def _segment_sections(self, text: str) -> Dict[str, str]:
        sections: Dict[str, str] = {}

        import re

        abstract_match = re.search(
            r"(?:ABSTRACT|Abstract)(.*?)(?:INTRODUCTION|Introduction|METHODS|Methods)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if abstract_match:
            sections["abstract"] = abstract_match.group(1).strip()

        intro_match = re.search(
            r"(?:INTRODUCTION|Introduction)(.*?)(?:METHODS|Methods|MATERIALS)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if intro_match:
            sections["introduction"] = intro_match.group(1).strip()

        methods_match = re.search(
            r"(?:METHODS|Methods|MATERIALS AND METHODS)(.*?)(?:RESULTS|Results)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if methods_match:
            sections["methods"] = methods_match.group(1).strip()

        results_match = re.search(
            r"(?:RESULTS|Results)(.*?)(?:DISCUSSION|Discussion|CONCLUSION|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if results_match:
            sections["results"] = results_match.group(1).strip()

        discussion_match = re.search(
            r"(?:DISCUSSION|Discussion)(.*?)(?:REFERENCES|References|ACKNOWLEDGMENTS)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if discussion_match:
            sections["discussion"] = discussion_match.group(1).strip()

        return sections
