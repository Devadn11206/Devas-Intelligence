import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, List, Optional
import httpx
from app.modules.ingestion.base import BaseSourceAdapter, CanonicalRecord
from app.db.models.intel import ContentType, Source


class ArxivAdapter(BaseSourceAdapter):
    """Adapter for arXiv Atom API (querying cs.LG, cs.AI, math.NA, etc.)."""

    async def fetch(self, config: dict[str, Any], since: Optional[datetime] = None) -> List[dict[str, Any]]:
        query = config.get("search_query", "cat:cs.LG OR cat:cs.AI OR cat:math.NA")
        max_results = config.get("max_results", 25)
        sort_by = config.get("sort_by", "submittedDate")
        sort_order = config.get("sort_order", "descending")

        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        resp = await self.client.get(url, params=params)
        resp.raise_for_status()

        # Parse XML root
        xml_text = resp.text
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        entries: List[dict[str, Any]] = []
        for entry in root.findall("atom:entry", ns):
            id_el = entry.find("atom:id", ns)
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            published_el = entry.find("atom:published", ns)
            updated_el = entry.find("atom:updated", ns)

            # Authors
            authors = [
                a.find("atom:name", ns).text.strip()
                for a in entry.findall("atom:author", ns)
                if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
            ]

            # Categories
            categories = [
                c.attrib.get("term")
                for c in entry.findall("atom:category", ns)
                if c.attrib.get("term")
            ]

            # PDF Link
            pdf_link = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_link = link.attrib.get("href")
                    break

            entries.append({
                "raw_id": id_el.text.strip() if id_el is not None and id_el.text else None,
                "title": title_el.text.strip() if title_el is not None and title_el.text else "",
                "summary": summary_el.text.strip() if summary_el is not None and summary_el.text else "",
                "published": published_el.text.strip() if published_el is not None and published_el.text else "",
                "updated": updated_el.text.strip() if updated_el is not None and updated_el.text else "",
                "authors": authors,
                "categories": categories,
                "pdf_link": pdf_link,
            })

        return entries

    def parse(self, raw_items: List[dict[str, Any]]) -> List[dict[str, Any]]:
        # If raw_items contains raw XML payloads, extract entries first
        items_to_process = []
        for item in raw_items:
            if "raw_xml" in item:
                root = ET.fromstring(item["raw_xml"])
                ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
                for entry in root.findall("atom:entry", ns):
                    id_el = entry.find("atom:id", ns)
                    title_el = entry.find("atom:title", ns)
                    summary_el = entry.find("atom:summary", ns)
                    published_el = entry.find("atom:published", ns)
                    updated_el = entry.find("atom:updated", ns)
                    authors = [
                        a.find("atom:name", ns).text.strip()
                        for a in entry.findall("atom:author", ns)
                        if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
                    ]
                    categories = [
                        c.attrib.get("term")
                        for c in entry.findall("atom:category", ns)
                        if c.attrib.get("term")
                    ]
                    pdf_link = None
                    for link in entry.findall("atom:link", ns):
                        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                            pdf_link = link.attrib.get("href")
                            break
                    items_to_process.append({
                        "raw_id": id_el.text.strip() if id_el is not None and id_el.text else None,
                        "title": title_el.text.strip() if title_el is not None and title_el.text else "",
                        "summary": summary_el.text.strip() if summary_el is not None and summary_el.text else "",
                        "published": published_el.text.strip() if published_el is not None and published_el.text else "",
                        "updated": updated_el.text.strip() if updated_el is not None and updated_el.text else "",
                        "authors": authors,
                        "categories": categories,
                        "pdf_link": pdf_link,
                    })
            else:
                items_to_process.append(item)

        parsed = []
        for item in items_to_process:
            raw_id = item.get("raw_id", "")
            # Extract clean arXiv id e.g. 2403.12345 from http://arxiv.org/abs/2403.12345v1
            arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
            if "v" in arxiv_id and arxiv_id.rsplit("v", 1)[-1].isdigit():
                arxiv_id = arxiv_id.rsplit("v", 1)[0]

            canonical_url = f"https://arxiv.org/abs/{arxiv_id}"

            # Parse published timestamp
            pub_date = datetime.now(timezone.utc)
            if item.get("published"):
                try:
                    pub_date = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            # Clean newlines from title and summary
            title = " ".join(item.get("title", "").split())
            summary = " ".join(item.get("summary", "").split())

            parsed.append({
                "external_id": arxiv_id,
                "canonical_url": canonical_url,
                "title": title,
                "summary_raw": summary,
                "authors": item.get("authors", []),
                "tags": item.get("categories", []),
                "published_at": pub_date,
                "metadata": {
                    "pdf_url": item.get("pdf_link"),
                    "arxiv_id": arxiv_id,
                    "categories": item.get("categories", []),
                },
            })
        return parsed

    def normalize(self, parsed_items: List[dict[str, Any]], source: Source) -> List[CanonicalRecord]:
        records = []
        for item in parsed_items:
            records.append(
                CanonicalRecord(
                    external_id=item["external_id"],
                    canonical_url=item["canonical_url"],
                    content_type=ContentType.PAPER,
                    title=item["title"],
                    summary_raw=item["summary_raw"],
                    content_raw=item["summary_raw"],
                    authors=item.get("authors", []),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                    published_at=item["published_at"],
                )
            )
        return records

