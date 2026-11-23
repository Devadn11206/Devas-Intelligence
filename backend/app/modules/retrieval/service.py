import time
import uuid
import re
from typing import Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.intel import Document, EntityLink, ContentType
from app.modules.retrieval.query_parser import (
    SearchRequest,
    normalize_query_for_cache,
)
from app.modules.retrieval.query_expander import expand_technical_query
from app.modules.retrieval.retriever import DualPathRetriever, ChunkCandidate
from app.modules.retrieval.reranker import (
    FusedChunkCandidate,
    reciprocal_rank_fusion,
    cross_encoder_rerank,
)
from app.modules.retrieval.cache import SearchCache


def highlight_snippet(text: str, query: str, max_chars: int = 240) -> str:
    """Extracts a focused snippet around the first matching term, or the start of the text."""
    if not text:
        return ""
    words = [w.strip() for w in re.split(r"\s+", query) if len(w.strip()) > 2]
    first_idx = -1
    for w in words:
        pos = text.lower().find(w.lower())
        if pos != -1:
            first_idx = pos
            break

    if first_idx == -1:
        snippet = text[:max_chars].strip()
        if len(text) > max_chars:
            snippet += "..."
        return snippet

    start = max(0, first_idx - 60)
    end = min(len(text), start + max_chars)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


class RetrievalService:
    """Coordinates Dual-Path Candidate Retrieval with Domain-Aware Expansion,

    Reciprocal Rank Fusion (RRF), Cross-Encoder Re-Ranking, and Provenance Scoring.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retriever = DualPathRetriever(db)

    async def search(self, req: SearchRequest) -> dict:
        start_time = time.perf_counter()

        # 1. Domain-Aware Query Expansion (< 5ms)
        expansion = expand_technical_query(req.query)
        expanded_terms = expansion["expanded_terms"]
        semantic_query = expansion["semantic_query"]

        # 2. Check Redis Query Cache
        canonical_key = normalize_query_for_cache(req)
        cache_key = SearchCache.generate_cache_key(canonical_key)
        cached_result = await SearchCache.get(cache_key)

        if cached_result is not None:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            cached_result["cache_hit"] = True
            cached_result["latency_ms"] = elapsed_ms
            cached_result["expanded_terms"] = expanded_terms
            return cached_result

        # 3. Dual-Signal Candidate Fetch (top_k * 3 candidates)
        fetch_limit = max(50, req.top_k * 3)
        lexical_cands: List[ChunkCandidate] = []
        vector_cands: List[ChunkCandidate] = []

        if req.mode in ("hybrid", "lexical"):
            lexical_cands = await self.retriever.fetch_lexical_candidates(
                req, limit=fetch_limit, expanded_terms=expanded_terms
            )

        if req.mode in ("hybrid", "vector"):
            vector_cands = await self.retriever.fetch_vector_candidates(
                req, limit=fetch_limit, semantic_query=semantic_query
            )

        total_candidates = len(set([c.chunk_id for c in lexical_cands] + [c.chunk_id for c in vector_cands]))

        # 4. Fetch lightweight metadata for candidate documents to enable RRF authority boosts
        cand_doc_ids = list(set([c.document_id for c in lexical_cands] + [c.document_id for c in vector_cands]))
        doc_metadata_map: Dict[uuid.UUID, dict] = {}

        if cand_doc_ids:
            doc_stmt = select(Document.id, Document.title, Document.tags).where(Document.id.in_(cand_doc_ids))
            doc_rows = (await self.db.execute(doc_stmt)).all()
            for r in doc_rows:
                doc_metadata_map[r.id] = {
                    "title": r.title,
                    "tags": r.tags or [],
                    "has_code_link": False,
                }

            # Check for verified entity links (Paper<->Repo consensus)
            link_stmt = select(EntityLink.source_entity_id, EntityLink.target_entity_id).where(
                or_(
                    EntityLink.source_entity_id.in_(cand_doc_ids),
                    EntityLink.target_entity_id.in_(cand_doc_ids),
                )
            )
            link_rows = (await self.db.execute(link_stmt)).all()
            for s_id, t_id in link_rows:
                if s_id in doc_metadata_map:
                    doc_metadata_map[s_id]["has_code_link"] = True
                if t_id in doc_metadata_map:
                    doc_metadata_map[t_id]["has_code_link"] = True

        all_query_terms = [req.query] + expanded_terms

        # 5. Fusion & Re-Ranking
        if req.mode == "hybrid":
            fused = reciprocal_rank_fusion(
                lexical_cands,
                vector_cands,
                k=60,
                top_fused=max(30, req.top_k * 3),
                doc_metadata_map=doc_metadata_map,
                query_terms=all_query_terms,
            )
            reranked = cross_encoder_rerank(req.query, fused)
        elif req.mode == "lexical":
            fused = reciprocal_rank_fusion(
                lexical_cands,
                [],
                k=60,
                top_fused=req.top_k * 3,
                doc_metadata_map=doc_metadata_map,
                query_terms=all_query_terms,
            )
            reranked = fused
        else:  # mode == "vector"
            fused = reciprocal_rank_fusion(
                [],
                vector_cands,
                k=60,
                top_fused=req.top_k * 3,
                doc_metadata_map=doc_metadata_map,
                query_terms=all_query_terms,
            )
            reranked = fused

        # 6. Document-Level Aggregation & Chunk Deduplication (<= 2 chunks per doc)
        doc_ids = list(dict.fromkeys([c.document_id for c in reranked]))

        if not doc_ids:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            res_dict = {
                "query": req.query,
                "expanded_terms": expanded_terms,
                "mode": req.mode,
                "total_candidates": 0,
                "latency_ms": elapsed_ms,
                "cache_hit": False,
                "facets": {"paper": 0, "repo": 0, "model": 0, "article": 0, "tool": 0},
                "results": [],
            }
            await SearchCache.set(cache_key, res_dict, ttl=300)
            return res_dict

        # Fetch Documents with sources
        docs_res = await self.db.execute(
            select(Document)
            .options(selectinload(Document.source))
            .where(Document.id.in_(doc_ids))
        )
        docs_by_id: Dict[uuid.UUID, Document] = {d.id: d for d in docs_res.scalars().all()}

        # Count linked repos / papers for these documents
        links_res = await self.db.execute(
            select(EntityLink)
            .options(selectinload(EntityLink.source_entity), selectinload(EntityLink.target_entity))
            .where(
                or_(
                    EntityLink.source_entity_id.in_(doc_ids),
                    EntityLink.target_entity_id.in_(doc_ids),
                )
            )
        )
        links = links_res.scalars().all()

        linked_repos_map: Dict[uuid.UUID, int] = {did: 0 for did in doc_ids}
        linked_papers_map: Dict[uuid.UUID, int] = {did: 0 for did in doc_ids}

        for l in links:
            if l.source_entity_id in doc_ids and l.target_entity:
                if l.target_entity.content_type == ContentType.REPO:
                    linked_repos_map[l.source_entity_id] += 1
                elif l.target_entity.content_type == ContentType.PAPER:
                    linked_papers_map[l.source_entity_id] += 1
            if l.target_entity_id in doc_ids and l.source_entity:
                if l.source_entity.content_type == ContentType.REPO:
                    linked_repos_map[l.target_entity_id] += 1
                elif l.source_entity.content_type == ContentType.PAPER:
                    linked_papers_map[l.target_entity_id] += 1

        # Chunk deduplication: keep at most 2 distinct chunks per document
        doc_chunk_counts: Dict[uuid.UUID, int] = {}
        results = []
        facets: Dict[str, int] = {"paper": 0, "repo": 0, "model": 0, "article": 0, "tool": 0}

        # Normalize score range for relevance_score (0.0 to 1.0)
        max_rerank = max([c.rerank_score for c in reranked], default=1.0)
        if max_rerank <= 0:
            max_rerank = 1.0

        for chunk in reranked:
            did = chunk.document_id
            count = doc_chunk_counts.get(did, 0)
            if count >= 2:
                continue

            doc = docs_by_id.get(did)
            if not doc:
                continue

            doc_chunk_counts[did] = count + 1

            c_type = doc.content_type.value if hasattr(doc.content_type, "value") else str(doc.content_type)
            if count == 0:
                facets[c_type] = facets.get(c_type, 0) + 1

            matched_snippet = highlight_snippet(chunk.content, req.query)
            normalized_relevance = min(1.0, max(0.0, round(chunk.rerank_score / max_rerank, 4)))

            results.append({
                "document_id": str(doc.id),
                "chunk_id": str(chunk.chunk_id),
                "section_type": chunk.section_type,
                "title": doc.title,
                "content_type": c_type,
                "canonical_url": doc.canonical_url,
                "source_name": doc.source.name if doc.source else "Source",
                "published_at": doc.published_at.isoformat() if doc.published_at else None,
                "matched_snippet": matched_snippet,
                "summary_raw": doc.summary_raw,
                "summary_ai": doc.summary_ai,
                "tags": doc.tags or [],
                "linked_repos_count": linked_repos_map.get(doc.id, 0),
                "linked_papers_count": linked_papers_map.get(doc.id, 0),
                "lexical_rank": chunk.lexical_rank,
                "vector_rank": chunk.vector_rank,
                "rrf_score": round(chunk.rrf_score, 6),
                "rerank_score": round(chunk.rerank_score, 4),
                "relevance_score": normalized_relevance,
                "matched_terms": chunk.matched_terms,
            })

            if len(results) >= req.top_k:
                break

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response_data = {
            "query": req.query,
            "expanded_terms": expanded_terms,
            "mode": req.mode,
            "total_candidates": total_candidates,
            "latency_ms": elapsed_ms,
            "cache_hit": False,
            "facets": facets,
            "results": results,
        }

        # Cache response
        await SearchCache.set(cache_key, response_data, ttl=300)
        return response_data

    async def suggest(self, q: str, limit: int = 6) -> List[dict]:
        """Provides fast prefix/trigram autocomplete suggestions for titles and tags."""
        if not q or len(q.strip()) < 1:
            return []

        clean = q.strip()
        pattern = f"%{clean}%"

        stmt = (
            select(Document.id, Document.title, Document.content_type, Document.tags)
            .where(or_(Document.title.ilike(pattern), Document.tags.contains([clean.lower()])))
            .order_by(Document.published_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        suggestions = []
        for r in rows:
            suggestions.append({
                "id": str(r.id),
                "title": r.title,
                "content_type": r.content_type.value if hasattr(r.content_type, "value") else str(r.content_type),
                "tags": r.tags or [],
            })
        return suggestions


# Module-level alias matching user reference
HybridRetrievalService = RetrievalService
