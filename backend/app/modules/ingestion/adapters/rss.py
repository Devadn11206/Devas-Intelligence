import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, List, Optional
from email.utils import parsedate_to_datetime
import httpx
from app.modules.ingestion.base import BaseSourceAdapter, CanonicalRecord
from app.db.models.intel import ContentType, Source


def strip_html_tags(text: str) -> str:
    """Removes HTML markup and unescapes text into clean plaintext."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


class RSSAdapter(BaseSourceAdapter):
    """Adapter for RSS 2.0 and Atom feeds (company engineering blogs, AI news)."""

    async def fetch(self, config: dict[str, Any], since: Optional[datetime] = None) -> List[dict[str, Any]]:
        feed_url = config.get("feed_url")
        if not feed_url:
            raise ValueError("RSSAdapter requires 'feed_url' in config")

        resp = await self.client.get(feed_url)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items: List[dict[str, Any]] = []

        # Check RSS 2.0 channel -> item
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                description = item.findtext("description") or ""
                content_encoded = (
                    item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                    or item.findtext("content")
                    or description
                )
                guid = item.findtext("guid") or link
                pub_date = item.findtext("pubDate") or ""
                author = item.findtext("author") or item.findtext("{http://purl.org/dc/elements/1.1/}creator") or ""

                items.append({
                    "guid": guid,
                    "title": title,
                    "link": link,
                    "description": description,
                    "content_encoded": content_encoded,
                    "pubDate": pub_date,
                    "author": author,
                    "feed_url": feed_url,
                })
        else:
            # Check Atom feed -> entry
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns) or root.findall("entry"):
                title = entry.findtext("atom:title", namespaces=ns) or entry.findtext("title") or ""
                link_el = entry.find("atom:link", ns) or entry.find("link")
                link = link_el.attrib.get("href") if link_el is not None else ""
                summary = (
                    entry.findtext("atom:summary", namespaces=ns)
                    or entry.findtext("summary")
                    or ""
                )
                content = (
                    entry.findtext("atom:content", namespaces=ns)
                    or entry.findtext("content")
                    or summary
                )
                guid = entry.findtext("atom:id", namespaces=ns) or entry.findtext("id") or link
                published = (
                    entry.findtext("atom:published", namespaces=ns)
                    or entry.findtext("published")
                    or entry.findtext("atom:updated", namespaces=ns)
                    or entry.findtext("updated")
                    or ""
                )
                author = (
                    entry.findtext("atom:author/atom:name", namespaces=ns)
                    or entry.findtext("author/name")
                    or ""
                )

                items.append({
                    "guid": guid,
                    "title": title,
                    "link": link,
                    "description": summary or content,
                    "content_encoded": content,
                    "pubDate": published,
                    "author": author,
                    "feed_url": feed_url,
                })

        return items

    def parse(self, raw_items: List[dict[str, Any]]) -> List[dict[str, Any]]:
        parsed = []
        for item in raw_items:
            guid = item.get("guid") or item.get("link")
            link = item.get("link") or guid
            if not link:
                continue

            pub_date = datetime.now(timezone.utc)
            if item.get("pubDate"):
                try:
                    # Attempt RFC-2822 or ISO parsing
                    pub_date = parsedate_to_datetime(item["pubDate"])
                except Exception:
                    try:
                        pub_date = datetime.fromisoformat(item["pubDate"].replace("Z", "+00:00"))
                    except Exception:
                        pass

            title = item.get("title", "").strip()
            raw_desc = item.get("description", "").strip()
            raw_content = item.get("content_encoded", "").strip() or raw_desc
            clean_desc = strip_html_tags(raw_desc)
            clean_content = strip_html_tags(raw_content)

            if not clean_content:
                clean_content = f"Technical news and engineering post discussing {title}."
            if not clean_desc or clean_desc.lower().startswith("no raw abstract"):
                clean_desc = clean_content[:400]

            summary = clean_desc[:400]
            authors = [item["author"].strip()] if item.get("author") else []

            parsed.append({
                "external_id": guid,
                "canonical_url": link,
                "title": title,
                "summary_raw": summary,
                "content_raw": clean_content[:4000],
                "authors": authors,
                "tags": ["blog", "article"],
                "published_at": pub_date,
                "metadata": {
                    "feed_url": item.get("feed_url"),
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
                    content_type=ContentType.ARTICLE,
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
