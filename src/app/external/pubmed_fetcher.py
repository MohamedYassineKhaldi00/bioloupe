from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from xml.etree import ElementTree as ET

from app.external.base_fetcher import BaseFetcher


class PubMedFetcher(BaseFetcher):
    def __init__(self, api_key: Optional[str] = None):
        rate_limit = 0.1 if api_key else 0.34
        super().__init__(
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            rate_limit=rate_limit
        )
        self.api_key = api_key

    async def search(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        pmids = await self._search_pmids(query, start_date, end_date, max_results)

        publications: List[Dict[str, Any]] = []
        batch_size = 200

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            if not batch:
                continue
            batch_pubs = await self._fetch_details(batch)
            publications.extend(batch_pubs)

        return publications

    async def _search_pmids(
        self,
        query: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        max_results: int
    ) -> List[str]:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json"
        }

        if self.api_key:
            params["api_key"] = self.api_key

        if start_date and end_date:
            params["datetype"] = "pdat"
            params["mindate"] = start_date.strftime('%Y/%m/%d')
            params["maxdate"] = end_date.strftime('%Y/%m/%d')

        response = await self._rate_limited_request(
            "GET",
            f"{self.base_url}/esearch.fcgi",
            params=params
        )

        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])

    async def _fetch_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }

        if self.api_key:
            params["api_key"] = self.api_key

        response = await self._rate_limited_request(
            "GET",
            f"{self.base_url}/efetch.fcgi",
            params=params
        )

        return self._parse_pubmed_xml(response.text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        root = ET.fromstring(xml_text)
        publications: List[Dict[str, Any]] = []

        for article in root.findall(".//PubmedArticle"):
            pub = self._extract_article_data(article)
            publications.append(pub)

        return publications

    def _extract_article_data(self, article: ET.Element) -> Dict[str, Any]:
        medline_citation = article.find("MedlineCitation")
        pmid_elem = medline_citation.find("PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""

        article_elem = medline_citation.find("Article")
        title_elem = article_elem.find("ArticleTitle") if article_elem is not None else None
        title = title_elem.text if title_elem is not None else ""

        abstract = ""
        if article_elem is not None:
            abstract_elem = article_elem.find("Abstract")
            if abstract_elem is not None:
                abstract_texts = abstract_elem.findall(".//AbstractText")
                abstract = " ".join([at.text or "" for at in abstract_texts])

        authors: List[str] = []
        if article_elem is not None:
            author_list = article_elem.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    if last_name is not None and fore_name is not None:
                        authors.append(f"{fore_name.text} {last_name.text}")

        journal = article_elem.find(".//Journal/Title") if article_elem is not None else None
        journal_name = journal.text if journal is not None else ""

        pub_date = article_elem.find(".//PubDate") if article_elem is not None else None
        pub_date_str = self._extract_pub_date(pub_date)

        doi_elem = article_elem.find(".//ELocationID[@EIdType='doi']") if article_elem is not None else None
        doi = doi_elem.text if doi_elem is not None else None

        return {
            "source": "pubmed",
            "external_id": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal_name,
            "publication_date": pub_date_str,
            "doi": doi,
            "metadata": {
                "pmid": pmid,
                "source": "pubmed"
            }
        }

    def _extract_pub_date(self, pub_date_elem: Optional[ET.Element]) -> str:
        if pub_date_elem is None:
            return ""

        year = pub_date_elem.find("Year")
        month = pub_date_elem.find("Month")
        day = pub_date_elem.find("Day")

        if year is not None and year.text:
            date_str = year.text
            if month is not None and month.text:
                date_str += f"-{month.text.zfill(2)}"
                if day is not None and day.text:
                    date_str += f"-{day.text.zfill(2)}"
            return date_str

        return ""

    async def fetch_by_id(self, pmid: str) -> Dict[str, Any]:
        publications = await self._fetch_details([pmid])
        return publications[0] if publications else {}
