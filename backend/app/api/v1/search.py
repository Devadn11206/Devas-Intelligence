from datetime import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.retrieval.query_parser import SearchRequest
from app.modules.retrieval.service import RetrievalService
from app.schemas.search import (
    SearchRequestSchema,
    SearchResponse,
    SuggestionItem,
)

router = APIRouter(prefix="/search", tags=["Unified Hybrid Search & Discovery"])


@router.post("", response_model=SearchResponse)
async def execute_search(
    payload: SearchRequestSchema,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Executes dual-path hybrid retrieval (Lexical BM25 + Dense Vector) with Reciprocal Rank Fusion

    and Cross-Encoder Reranking.
    """
    req = SearchRequest(
        query=payload.query,
        content_types=payload.content_types,
        tags=payload.tags,
        date_from=payload.date_from,
        date_to=payload.date_to,
        has_linked_code=payload.has_linked_code,
        top_k=payload.top_k,
        mode=payload.mode,
    )
    service = RetrievalService(db)
    result = await service.search(req)
    return SearchResponse(**result)


@router.get("", response_model=SearchResponse)
async def get_search(
    q: str = Query(..., min_length=1, max_length=500),
    mode: Literal["hybrid", "lexical", "vector"] = Query(default="hybrid"),
    content_types: Optional[List[str]] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    has_linked_code: Optional[bool] = Query(default=None),
    top_k: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """GET convenience endpoint for unified hybrid search."""
    req = SearchRequest(
        query=q,
        content_types=content_types,
        tags=tags,
        date_from=date_from,
        date_to=date_to,
        has_linked_code=has_linked_code,
        top_k=top_k,
        mode=mode,
    )
    service = RetrievalService(db)
    result = await service.search(req)
    return SearchResponse(**result)


@router.get("/suggest", response_model=List[SuggestionItem])
async def get_suggestions(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> List[SuggestionItem]:
    """Returns fast prefix/trigram autocomplete suggestions for the Command Palette."""
    service = RetrievalService(db)
    items = await service.suggest(q, limit=limit)
    return [SuggestionItem(**item) for item in items]
