import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple, Type
import httpx
from pydantic import BaseModel, Field
from app.db.models.intel import ContentType, Source


class CanonicalRecord(BaseModel):
    """Normalized content record produced by all source adapters."""
    external_id: str = Field(..., description="Unique ID within source")
    canonical_url: str = Field(..., description="Canonical permalink")
    content_type: ContentType
    title: str = Field(..., min_length=1)
    summary_raw: str = Field(default="")
    content_raw: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        """Computes SHA-256 hash of normalized title and content for change detection."""
        body = (self.content_raw or self.summary_raw or "").strip()
        payload = f"{self.title.strip()}::{body}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BaseSourceAdapter(ABC):
    """Contract for all external data source adapters."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "DEVA-Intelligence-Bot/0.2.0 (+https://deva.intel)",
                "Accept": "application/json, application/atom+xml, application/xml, text/xml",
            },
            follow_redirects=True,
        )

    @abstractmethod
    async def fetch(self, config: dict[str, Any], since: Optional[datetime] = None) -> List[dict[str, Any]]:
        """Fetch raw items from external API or feed."""
        pass

    @abstractmethod
    def parse(self, raw_items: List[dict[str, Any]]) -> List[dict[str, Any]]:
        """Parse raw entries into structured intermediate dictionaries."""
        pass

    @abstractmethod
    def normalize(self, parsed_items: List[dict[str, Any]], source: Source) -> List[CanonicalRecord]:
        """Normalize parsed items into standard CanonicalRecord schemas."""
        pass

    def validate(
        self, records: List[Any]
    ) -> Tuple[List[CanonicalRecord], List[dict[str, Any]]]:
        """Validates canonical records; returns (valid_records, quarantined_items)."""
        valid: List[CanonicalRecord] = []
        quarantined: List[dict[str, Any]] = []

        for item in records:
            try:
                if isinstance(item, CanonicalRecord):
                    valid.append(item)
                elif isinstance(item, dict):
                    valid.append(CanonicalRecord(**item))
                else:
                    quarantined.append({
                        "raw_payload": {"item": str(item)},
                        "validation_error": f"Invalid type {type(item)}",
                    })
            except Exception as e:
                raw = item if isinstance(item, dict) else (item.dict() if hasattr(item, "dict") else {"item": str(item)})
                quarantined.append({
                    "external_id": getattr(item, "external_id", None) if not isinstance(item, dict) else item.get("external_id"),
                    "raw_payload": raw,
                    "validation_error": str(e),
                })

        return valid, quarantined


class AdapterRegistry:
    """Registry maintaining mappings of adapter_key to adapter implementations."""
    _adapters: dict[str, Type[BaseSourceAdapter]] = {}

    @classmethod
    def register(cls, key: str, adapter_cls: Type[BaseSourceAdapter]) -> None:
        cls._adapters[key] = adapter_cls

    @classmethod
    def get(cls, key: str, client: Optional[httpx.AsyncClient] = None) -> BaseSourceAdapter:
        adapter_cls = cls._adapters.get(key)
        if not adapter_cls:
            raise ValueError(f"No ingestion adapter registered for key: '{key}'")
        return adapter_cls(client=client)

    @classmethod
    def list_keys(cls) -> List[str]:
        return list(cls._adapters.keys())

