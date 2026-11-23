from datetime import datetime, timezone
from typing import Any, List, Optional
import httpx
from app.modules.ingestion.base import BaseSourceAdapter, CanonicalRecord
from app.db.models.intel import ContentType, Source


class HuggingFaceAdapter(BaseSourceAdapter):
    """Adapter for Hugging Face Hub Models API."""

    async def fetch(self, config: dict[str, Any], since: Optional[datetime] = None) -> List[dict[str, Any]]:
        url = "https://huggingface.co/api/models"
        params = {
            "limit": min(config.get("limit", 25), 50),
            "sort": config.get("sort", "downloads"),
            "direction": -1,
            "full": "true",
        }
        if config.get("filter"):
            params["filter"] = config["filter"]

        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def parse(self, raw_items: List[dict[str, Any]]) -> List[dict[str, Any]]:
        parsed = []
        for item in raw_items:
            model_id = item.get("id") or item.get("modelId")
            if not model_id:
                continue

            canonical_url = f"https://huggingface.co/{model_id}"

            pub_date = datetime.now(timezone.utc)
            if item.get("lastModified"):
                try:
                    pub_date = datetime.fromisoformat(item["lastModified"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            author = model_id.split("/")[0] if "/" in model_id else "community"
            raw_tags = item.get("tags", [])
            # Filter out internal HF key-value metadata tags containing colons e.g. base_model:, arxiv:, doi:, license:, region:, dataset:
            clean_tags = []
            for t in raw_tags:
                if not isinstance(t, str):
                    continue
                t_str = t.strip()
                if not t_str or ":" in t_str or t_str.startswith("license") or t_str.startswith("region"):
                    continue
                clean_tags.append(t_str)

            if pipeline_tag and ":" not in pipeline_tag and pipeline_tag not in clean_tags:
                clean_tags.append(pipeline_tag)

            parsed.append({
                "external_id": model_id,
                "canonical_url": canonical_url,
                "title": model_id,
                "summary_raw": f"Hugging Face model: {model_id} ({pipeline_tag}). Downloads: {item.get('downloads', 0):,}, Likes: {item.get('likes', 0):,}",
                "content_raw": item.get("description") or f"Model weights and checkpoints for {model_id}",
                "authors": [author],
                "tags": clean_tags,
                "published_at": pub_date,
                "metadata": {
                    "downloads": item.get("downloads", 0),
                    "likes": item.get("likes", 0),
                    "pipeline_tag": pipeline_tag,
                    "private": item.get("private", False),
                    "sha": item.get("sha"),
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
                    content_type=ContentType.MODEL,
                    title=item["title"],
                    summary_raw=item["summary_raw"],
                    content_raw=item["content_raw"],
                    authors=item.get("authors", []),
                    tags=[t for t in item.get("tags", []) if t],
                    metadata=item.get("metadata", {}),
                    published_at=item["published_at"],
                )
            )
        return records
