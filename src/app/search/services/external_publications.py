from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ExternalPublicationClient:
    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()
        self._timeout = httpx.Timeout(12.0, connect=5.0)

    async def search_pubmed(self, query: str, page: int, limit: int) -> List[Dict[str, Any]]:
        params = {
            "format": "summary",
            "term": query,
            "size": limit,
            "page": page,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._settings.pubmed_search_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("PubMed search failed", extra={"error": str(exc)})
            return []

        records = payload.get("records") or []
        return [self._normalize_pubmed_record(record) for record in records]

    async def search_arxiv(self, query: str, page: int, limit: int) -> List[Dict[str, Any]]:
        start = (page - 1) * limit
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": limit,
            "sortBy": "relevance",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._settings.arxiv_search_url, params=params)
                response.raise_for_status()
                text = response.text
        except Exception as exc:
            logger.warning("arXiv search failed", extra={"error": str(exc)})
            return []

        return self._parse_arxiv_feed(text)

    def _normalize_pubmed_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": record.get("title") or record.get("article_title") or "PubMed result",
            "snippet": record.get("abstract") or record.get("excerpt") or "",
            "publication_id": str(record.get("uid", record.get("pmid", ""))),
            "metadata": record,
        }

    def _parse_arxiv_feed(self, body: str) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return []

        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", namespace)
        results: List[Dict[str, Any]] = []
        for entry in entries:
            title = entry.find("atom:title", namespace)
            summary = entry.find("atom:summary", namespace)
            id_node = entry.find("atom:id", namespace)
            results.append(
                {
                    "title": title.text.strip() if title is not None and title.text else "arXiv result",
                    "snippet": summary.text.strip() if summary is not None and summary.text else "",
                    "publication_id": id_node.text.strip() if id_node is not None and id_node.text else "",
                    "metadata": {"entry": ET.tostring(entry, encoding="unicode")},
                }
            )
        return results
