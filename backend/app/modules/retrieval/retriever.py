import uuid
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.intel import Document, DocumentChunk, EntityLink, RelationType, ContentType
from app.modules.retrieval.query_parser import SearchRequest, sanitize_tsquery_input
from app.core.embeddings import get_embedding_service


@dataclass
class ChunkCandidate:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    section_type: str
    content: str
    token_count: int
    lexical_rank: Optional[int] = None
    lexical_score: Optional[float] = None
    vector_rank: Optional[int] = None
    vector_distance: Optional[float] = None


class DualPathRetriever:
    """Retrieves top-N chunk candidates via Lexical (tsvector + ILIKE fallback) and Dense Vector paths."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    def _build_filter_clauses(self, req: SearchRequest):
        clauses = []
        if req.content_types:
            clauses.append(Document.content_type.in_(req.content_types))
        if req.tags:
            clauses.append(Document.tags.overlap(req.tags))
        if req.date_from:
            clauses.append(Document.published_at >= req.date_from)
        if req.date_to:
            clauses.append(Document.published_at <= req.date_to)
        if req.has_linked_code is True:
            linked_code_subq = (
                select(1)
                .select_from(EntityLink)
                .join(Document, EntityLink.target_entity_id == Document.id)
                .where(
                    or_(
                        and_(
                            EntityLink.source_entity_id == DocumentChunk.document_id,
                            EntityLink.relation_type == RelationType.IMPLEMENTS,
                            Document.content_type == ContentType.REPO,
                        ),
                        and_(
                            EntityLink.target_entity_id == DocumentChunk.document_id,
                            EntityLink.relation_type == RelationType.IMPLEMENTS,
                        ),
                    )
                )
            )
            clauses.append(linked_code_subq.exists())

        return clauses

    async def fetch_lexical_candidates(
        self,
        req: SearchRequest,
        limit: int = 50,
        expanded_terms: Optional[List[str]] = None,
    ) -> List[ChunkCandidate]:
        """Fetches top-N chunks using PostgreSQL websearch_to_tsquery, with ILIKE/tag matching."""
        sanitized_q = sanitize_tsquery_input(req.query)
        if not sanitized_q:
            return []

        # 1. Primary: full-text tsquery search
        tsquery_func = func.websearch_to_tsquery("english", sanitized_q)
        rank_func = func.ts_rank_cd(DocumentChunk.search_vector, tsquery_func).label("rank_score")

        filters = self._build_filter_clauses(req)
        filters.append(DocumentChunk.search_vector.op("@@")(tsquery_func))

        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DocumentChunk.section_type,
                DocumentChunk.content,
                DocumentChunk.token_count,
                rank_func,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(and_(*filters))
            .order_by(rank_func.desc())
            .limit(limit)
        )

        res = await self.db.execute(stmt)
        rows = res.all()

        candidates: List[ChunkCandidate] = []
        seen_chunks = set()

        for idx, row in enumerate(rows):
            seen_chunks.add(row.id)
            candidates.append(
                ChunkCandidate(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    chunk_index=row.chunk_index,
                    section_type=row.section_type,
                    content=row.content,
                    token_count=row.token_count,
                    lexical_rank=idx + 1,
                    lexical_score=float(row.rank_score) if row.rank_score is not None else 0.0,
                )
            )

        # 2. Secondary ILIKE / Tag expansion pass if primary yielded fewer than limit
        search_terms = [req.query.strip().lower()]
        if expanded_terms:
            search_terms.extend([t.strip().lower() for t in expanded_terms[:4]])

        if len(candidates) < limit:
            ilike_conditions = []
            for term in search_terms:
                if len(term) >= 2:
                    ilike_conditions.append(Document.title.ilike(f"%{term}%"))
                    ilike_conditions.append(Document.summary_raw.ilike(f"%{term}%"))
                    ilike_conditions.append(DocumentChunk.content.ilike(f"%{term}%"))
                    ilike_conditions.append(Document.tags.contains([term]))

            if ilike_conditions:
                fallback_filters = self._build_filter_clauses(req)
                fallback_filters.append(or_(*ilike_conditions))

                fallback_stmt = (
                    select(
                        DocumentChunk.id,
                        DocumentChunk.document_id,
                        DocumentChunk.chunk_index,
                        DocumentChunk.section_type,
                        DocumentChunk.content,
                        DocumentChunk.token_count,
                    )
                    .join(Document, DocumentChunk.document_id == Document.id)
                    .where(and_(*fallback_filters))
                    .order_by(Document.published_at.desc())
                    .limit(limit - len(candidates))
                )

                fb_res = await self.db.execute(fallback_stmt)
                for row in fb_res.all():
                    if row.id in seen_chunks:
                        continue
                    seen_chunks.add(row.id)
                    candidates.append(
                        ChunkCandidate(
                            chunk_id=row.id,
                            document_id=row.document_id,
                            chunk_index=row.chunk_index,
                            section_type=row.section_type,
                            content=row.content,
                            token_count=row.token_count,
                            lexical_rank=len(candidates) + 1,
                            lexical_score=0.15,
                        )
                    )

        return candidates

    async def fetch_vector_candidates(
        self,
        req: SearchRequest,
        limit: int = 50,
        semantic_query: Optional[str] = None,
    ) -> List[ChunkCandidate]:
        """Fetches top-N chunks using pgvector cosine distance `<=>` against query embedding."""
        query_text = semantic_query if semantic_query else req.query
        query_vector = self.embedding_service.embed_query(query_text)

        filters = self._build_filter_clauses(req)
        filters.append(DocumentChunk.embedding.is_not(None))

        dist_expr = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.chunk_index,
                DocumentChunk.section_type,
                DocumentChunk.content,
                DocumentChunk.token_count,
                dist_expr,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(and_(*filters))
            .order_by("distance")
            .limit(limit)
        )

        res = await self.db.execute(stmt)
        rows = res.all()

        candidates: List[ChunkCandidate] = []
        for idx, row in enumerate(rows):
            candidates.append(
                ChunkCandidate(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    chunk_index=row.chunk_index,
                    section_type=row.section_type,
                    content=row.content,
                    token_count=row.token_count,
                    vector_rank=idx + 1,
                    vector_distance=float(row.distance) if row.distance is not None else 1.0,
                )
            )
        return candidates
