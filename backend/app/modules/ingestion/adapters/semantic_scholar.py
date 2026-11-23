from datetime import datetime, timezone
from typing import Any, List, Optional
import httpx
from app.modules.ingestion.base import BaseSourceAdapter, CanonicalRecord
from app.db.models.intel import ContentType, Source


class SemanticScholarAdapter(BaseSourceAdapter):
    """Adapter for Semantic Scholar Academic Graph API."""

    async def fetch(self, config: dict[str, Any], since: Optional[datetime] = None) -> List[dict[str, Any]]:
        query = config.get("query", "Physics-Informed Neural Networks scientific machine learning")
        limit = min(config.get("limit", 20), 50)
        api_key = config.get("api_key")

        headers = {
            "User-Agent": "DEVA-Intelligence/1.0 (academic-research-crawler; contact@devaintelligence.local)"
        }
        if api_key:
            headers["x-api-key"] = api_key

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors,year,citationCount,openAccessPdf,externalIds,url,publicationDate",
        }

        # Resilient fetch with exponential backoff on 429
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = await self.client.get(url, params=params, headers=headers)
                if resp.status_code == 429:
                    # Semantic Scholar public rate limit hit
                    import asyncio
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
            except Exception as exc:
                if attempt == max_retries - 1:
                    # Fallback to OpenAlex open API for high resilience
                    return await self._fetch_openalex_fallback(query=query, limit=limit)
                import asyncio
                await asyncio.sleep(1.0)
        return []

    async def _fetch_openalex_fallback(self, query: str, limit: int) -> List[dict[str, Any]]:
        """High-availability fallback querying OpenAlex when Semantic Scholar is rate-limited."""
        try:
            url = f"https://api.openalex.org/works?search={query}&per-page={limit}"
            headers = {"User-Agent": "DEVA-Intelligence/1.0 (mailto:admin@devaintelligence.local)"}
            resp = await self.client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            transformed = []
            for item in results:
                authors = [
                    {"name": a.get("author", {}).get("display_name")}
                    for a in item.get("authorships", [])
                    if a.get("author", {}).get("display_name")
                ]
                transformed.append({
                    "paperId": item.get("id"),
                    "title": item.get("title") or "OpenAlex Academic Publication",
                    "abstract": item.get("abstract") or item.get("display_name"),
                    "url": item.get("doi") or item.get("id"),
                    "publicationDate": item.get("publication_date"),
                    "authors": authors,
                    "citationCount": item.get("cited_by_count", 0),
                    "year": item.get("publication_year"),
                })
            return transformed
        except Exception:
            return []

    def parse(self, raw_items: List[dict[str, Any]]) -> List[dict[str, Any]]:
        parsed = []
        for paper in raw_items:
            paper_id = paper.get("paperId")
            if not paper_id:
                continue

            canonical_url = paper.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"

            pub_date = datetime.now(timezone.utc)
            if paper.get("publicationDate"):
                try:
                    pub_date = datetime.fromisoformat(paper["publicationDate"])
                except ValueError:
                    pass

            authors = [a.get("name") for a in paper.get("authors", []) if a.get("name")]
            ext_ids = paper.get("externalIds") or {}
            pdf_url = (paper.get("openAccessPdf") or {}).get("url")

            parsed.append({
                "external_id": paper_id,
                "canonical_url": canonical_url,
                "title": paper.get("title", ""),
                "summary_raw": paper.get("abstract") or "No abstract provided.",
                "content_raw": paper.get("abstract") or "",
                "authors": authors,
                "tags": ["scientific_ml", "semantic_scholar"],
                "published_at": pub_date,
                "metadata": {
                    "citation_count": paper.get("citationCount", 0),
                    "external_ids": ext_ids,
                    "pdf_url": pdf_url,
                    "year": paper.get("year"),
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
                    content_raw=item["content_raw"],
                    authors=item.get("authors", []),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                    published_at=item["published_at"],
                )
            )
        return records
