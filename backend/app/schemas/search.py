import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class SearchRequestSchema(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    content_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_linked_code: Optional[bool] = None
    top_k: int = Field(default=10, ge=1, le=50)
    mode: Literal["hybrid", "lexical", "vector"] = "hybrid"


class SearchResultItem(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    section_type: str
    title: str
    content_type: str
    canonical_url: str
    source_name: str
    published_at: Optional[datetime] = None
    matched_snippet: str
    summary_ai: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    linked_repos_count: int = 0
    linked_papers_count: int = 0
    lexical_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    rrf_score: float
    rerank_score: float


class SearchResponse(BaseModel):
    query: str
    mode: str
    total_candidates: int
    latency_ms: float
    cache_hit: bool
    facets: Dict[str, int]
    results: List[SearchResultItem]


class SuggestionItem(BaseModel):
    id: uuid.UUID
    title: str
    content_type: str
    tags: List[str] = Field(default_factory=list)
