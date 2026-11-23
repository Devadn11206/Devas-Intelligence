import re
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    content_types: Optional[List[str]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    date_from: Optional[datetime] = Field(default=None)
    date_to: Optional[datetime] = Field(default=None)
    has_linked_code: Optional[bool] = Field(default=None)
    top_k: int = Field(default=10, ge=1, le=50)
    mode: Literal["hybrid", "lexical", "vector"] = Field(default="hybrid")


def sanitize_tsquery_input(raw_query: str) -> str:
    """Sanitizes raw user query for websearch_to_tsquery.

    Removes unbalanced quotes and illegal characters while preserving clean search phrases.
    """
    if not raw_query:
        return ""
    # Strip dangerous punctuation that can break parser
    cleaned = re.sub(r"[\x00\r\n\t]", " ", raw_query)
    # Balance quotes if unbalanced
    if cleaned.count('"') % 2 != 0:
        cleaned = cleaned.replace('"', ' ')
    # Normalize excessive spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_query_for_cache(req: SearchRequest) -> str:
    """Creates a canonical string representation of the search request for cache key generation."""
    ct = sorted(req.content_types) if req.content_types else []
    tg = sorted(req.tags) if req.tags else []
    d_from = req.date_from.isoformat() if req.date_from else ""
    d_to = req.date_to.isoformat() if req.date_to else ""
    hlc = str(req.has_linked_code) if req.has_linked_code is not None else ""
    clean_q = re.sub(r"\s+", " ", req.query.strip().lower())
    return f"q={clean_q}|mode={req.mode}|k={req.top_k}|ct={','.join(ct)}|tg={','.join(tg)}|df={d_from}|dt={d_to}|hlc={hlc}"
