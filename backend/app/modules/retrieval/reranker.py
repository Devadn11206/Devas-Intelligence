import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class FusedChunkCandidate:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    section_type: str
    content: str
    token_count: int
    lexical_rank: Optional[int]
    vector_rank: Optional[int]
    rrf_score: float
    rerank_score: float = 0.0
    matched_terms: List[str] = field(default_factory=list)


def reciprocal_rank_fusion(
    lexical_candidates: list,
    vector_candidates: list,
    k: int = 60,
    top_fused: int = 40,
    doc_metadata_map: Optional[Dict[uuid.UUID, dict]] = None,
    query_terms: Optional[List[str]] = None,
) -> List[FusedChunkCandidate]:
    """Computes RRF score across union of lexical and vector candidates:

        rrf_score = 1 / (k + rank_lexical) + 1 / (k + rank_vector)

    And applies lightweight calibrated domain authority boosts:
      - Exact Title / Tag Match Boost (+0.008): when query or expanded acronym matches document.title or tags.
      - Verified Code-Backed Boost (+0.004): when document has verified entity_links (Paper<->Repo).
    """
    chunk_map: Dict[uuid.UUID, FusedChunkCandidate] = {}
    doc_meta = doc_metadata_map or {}
    terms_lower = [t.lower().strip() for t in (query_terms or []) if len(t.strip()) > 1]

    for cand in lexical_candidates:
        cid = cand.chunk_id
        chunk_map[cid] = FusedChunkCandidate(
            chunk_id=cand.chunk_id,
            document_id=cand.document_id,
            chunk_index=cand.chunk_index,
            section_type=cand.section_type,
            content=cand.content,
            token_count=cand.token_count,
            lexical_rank=cand.lexical_rank,
            vector_rank=None,
            rrf_score=1.0 / (k + (cand.lexical_rank or 999)),
        )

    for cand in vector_candidates:
        cid = cand.chunk_id
        if cid in chunk_map:
            existing = chunk_map[cid]
            existing.vector_rank = cand.vector_rank
            existing.rrf_score += 1.0 / (k + (cand.vector_rank or 999))
        else:
            chunk_map[cid] = FusedChunkCandidate(
                chunk_id=cand.chunk_id,
                document_id=cand.document_id,
                chunk_index=cand.chunk_index,
                section_type=cand.section_type,
                content=cand.content,
                token_count=cand.token_count,
                lexical_rank=None,
                vector_rank=cand.vector_rank,
                rrf_score=1.0 / (k + (cand.vector_rank or 999)),
            )

    # Apply Calibrated Entity & Match Boosts
    for cand in chunk_map.values():
        meta = doc_meta.get(cand.document_id, {})
        title_lower = (meta.get("title") or "").lower()
        tags_lower = [str(t).lower() for t in (meta.get("tags") or [])]
        has_code_link = meta.get("has_code_link", False) or meta.get("linked_repos_count", 0) > 0

        matched: Set[str] = set()

        # Check matched terms in chunk content, title, tags
        content_lower = cand.content.lower()
        for term in terms_lower:
            if term in content_lower:
                matched.add(term)
            if term in title_lower:
                matched.add(term)
            if any(term in tg for tg in tags_lower):
                matched.add(term)

        cand.matched_terms = sorted(matched)

        # 1. Exact Title / Tag Match Boost (+0.008)
        title_or_tag_match = any(
            t in title_lower or any(t == tg for tg in tags_lower)
            for t in terms_lower
        )
        if title_or_tag_match:
            cand.rrf_score += 0.008

        # 2. Verified Code-Backed Boost (+0.004)
        if has_code_link:
            cand.rrf_score += 0.004

        # Initial rerank_score defaults to rrf_score
        cand.rerank_score = cand.rrf_score

    sorted_fused = sorted(chunk_map.values(), key=lambda x: x.rrf_score, reverse=True)
    return sorted_fused[:top_fused]


def cross_encoder_rerank(
    query: str,
    fused_candidates: List[FusedChunkCandidate],
) -> List[FusedChunkCandidate]:
    """Applies cross-encoder model to score fused candidates, preserving RRF boosts."""
    if not fused_candidates:
        return []

    from app.core.embeddings import get_embedding_service
    embedding_service = get_embedding_service()
    texts = [c.content for c in fused_candidates]

    try:
        rerank_results = embedding_service.rerank(query=query, documents=texts)
        res_by_idx = {r["index"]: float(r["score"]) for r in rerank_results}

        for idx, cand in enumerate(fused_candidates):
            cross_score = res_by_idx.get(idx, 0.0)
            # Combine normalized cross encoder with calibrated RRF boost
            cand.rerank_score = round(cross_score * 0.7 + cand.rrf_score * 0.3, 5)
    except Exception:
        # Fallback to rrf_score if cross encoder is unavailable or offline
        for cand in fused_candidates:
            cand.rerank_score = round(cand.rrf_score, 5)

    # Re-sort primarily by rerank_score, break ties with rrf_score
    return sorted(fused_candidates, key=lambda x: (x.rerank_score, x.rrf_score), reverse=True)
