import logging
import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.intel import (
    Document,
    DocumentChunk,
    EntityLink,
    RelationType,
    LinkMethod,
    ContentType,
    ProcessingStatus,
)
from app.modules.linking.extractors import (
    extract_github_urls,
    extract_huggingface_urls,
    extract_arxiv_ids,
    normalize_github_url,
    normalize_arxiv_id,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntityLinkerService:
    """Three-pass hybrid entity linker connecting research papers, code repositories, and models."""

    @staticmethod
    async def upsert_link(
        db: AsyncSession,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        relation_type: RelationType,
        confidence_score: float,
        link_method: LinkMethod,
        evidence_snippet: str,
    ) -> bool:
        """Upserts an EntityLink idempotently. Upgrades confidence score if a stronger link is found."""
        if source_id == target_id:
            return False

        # Check existing link
        res = await db.execute(
            select(EntityLink).where(
                EntityLink.source_entity_id == source_id,
                EntityLink.target_entity_id == target_id,
                EntityLink.relation_type == relation_type,
            )
        )
        existing = res.scalars().first()

        if existing:
            # Upgrade confidence if stronger
            if confidence_score > existing.confidence_score:
                existing.confidence_score = confidence_score
                existing.link_method = link_method
                existing.evidence_snippet = evidence_snippet
                existing.updated_at = utc_now()
                await db.commit()
            return False

        new_link = EntityLink(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relation_type=relation_type,
            confidence_score=confidence_score,
            link_method=link_method,
            evidence_snippet=evidence_snippet,
        )
        db.add(new_link)
        await db.commit()
        return True

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def link_document(self, doc_or_id: Any) -> List[EntityLink]:
        """Runs the three-pass entity linking pipeline for a given document or ID."""
        if not self.db:
            raise ValueError("AsyncSession required for instance link_document call")
        doc_id = doc_or_id.id if hasattr(doc_or_id, "id") else doc_or_id
        await self.link_document_class(self.db, doc_id)
        # Return all links associated with this document
        res = await self.db.execute(
            select(EntityLink).where(
                or_(
                    EntityLink.source_entity_id == doc_id,
                    EntityLink.target_entity_id == doc_id,
                )
            )
        )
        return list(res.scalars().all())

    @classmethod
    async def link_document_class(cls, db: AsyncSession, document_id: uuid.UUID) -> int:
        """Runs the three-pass entity linking pipeline for a given document."""
        res = await db.execute(select(Document).where(Document.id == document_id))
        doc = res.scalars().first()
        if not doc:
            return 0

        links_created = 0
        doc_body = f"{doc.title} {doc.summary_raw} {doc.content_raw or ''}"

        # ======================================================================
        # PASS 1 — Deterministic URL & ArXiv ID Match (confidence = 1.0)
        # ======================================================================

        # Case 1A: Document is a PAPER -> scan for GitHub or HF URLs
        if doc.content_type == ContentType.PAPER:
            gh_urls = extract_github_urls(doc_body)
            for gh_url in gh_urls:
                # Find matching repo in documents
                repo_res = await db.execute(
                    select(Document).where(
                        Document.content_type == ContentType.REPO,
                        Document.canonical_url.ilike(f"%{gh_url.replace('https://github.com/', '')}%"),
                    )
                )
                repo_match = repo_res.scalars().first()
                if repo_match:
                    # Repo implements Paper
                    created = await cls.upsert_link(
                        db=db,
                        source_id=repo_match.id,
                        target_id=doc.id,
                        relation_type=RelationType.IMPLEMENTS,
                        confidence_score=1.0,
                        link_method=LinkMethod.DETERMINISTIC_URL,
                        evidence_snippet=f"Paper cites code implementation: {gh_url}",
                    )
                    if created:
                        links_created += 1

            hf_urls = extract_huggingface_urls(doc_body)
            for hf_url in hf_urls:
                hf_res = await db.execute(
                    select(Document).where(
                        Document.content_type == ContentType.MODEL,
                        Document.canonical_url.ilike(f"%{hf_url.replace('https://huggingface.co/', '')}%"),
                    )
                )
                hf_match = hf_res.scalars().first()
                if hf_match:
                    created = await cls.upsert_link(
                        db=db,
                        source_id=hf_match.id,
                        target_id=doc.id,
                        relation_type=RelationType.IMPLEMENTS,
                        confidence_score=1.0,
                        link_method=LinkMethod.DETERMINISTIC_URL,
                        evidence_snippet=f"Paper links model weights: {hf_url}",
                    )
                    if created:
                        links_created += 1

        # Case 1B: Document is a REPO or MODEL -> scan for arXiv IDs in README / description
        elif doc.content_type in (ContentType.REPO, ContentType.MODEL):
            arxiv_ids = extract_arxiv_ids(doc_body)
            for aid in arxiv_ids:
                # Find matching paper by external_id or canonical_url
                paper_res = await db.execute(
                    select(Document).where(
                        Document.content_type == ContentType.PAPER,
                        or_(
                            Document.external_id.ilike(f"%{aid}%"),
                            Document.canonical_url.ilike(f"%{aid}%"),
                        ),
                    )
                )
                paper_match = paper_res.scalars().first()
                if paper_match:
                    created = await cls.upsert_link(
                        db=db,
                        source_id=doc.id,
                        target_id=paper_match.id,
                        relation_type=RelationType.IMPLEMENTS,
                        confidence_score=1.0,
                        link_method=LinkMethod.ARXIV_ID_MATCH,
                        evidence_snippet=f"Repository README cites arXiv paper: {aid}",
                    )
                    if created:
                        links_created += 1

        # ======================================================================
        # PASS 2 — Metadata Cross-Reference Match (confidence = 0.90)
        # ======================================================================
        doc_arxiv_id = normalize_arxiv_id(doc.metadata_.get("arxiv_id", "") or doc.external_id)
        if doc_arxiv_id and len(doc_arxiv_id) >= 6:
            # Query any cross-source documents sharing this arxiv_id
            cross_res = await db.execute(
                select(Document).where(
                    Document.id != doc.id,
                    or_(
                        Document.external_id == doc_arxiv_id,
                        Document.canonical_url.ilike(f"%{doc_arxiv_id}%"),
                    ),
                )
            )
            cross_docs = cross_res.scalars().all()
            for cd in cross_docs:
                rel = RelationType.USES_MODEL if doc.content_type == ContentType.MODEL else RelationType.RELATED_TO
                created = await cls.upsert_link(
                    db=db,
                    source_id=doc.id,
                    target_id=cd.id,
                    relation_type=rel,
                    confidence_score=0.90,
                    link_method=LinkMethod.ARXIV_ID_MATCH,
                    evidence_snippet=f"Cross-source metadata identifier match: {doc_arxiv_id}",
                )
                if created:
                    links_created += 1

        # ======================================================================
        # PASS 3 — Semantic Embedding + Author / Contributor Overlap (confidence = 0.72 - 0.85)
        # ======================================================================
        # Only evaluate if doc is paper or repo
        if doc.content_type in (ContentType.PAPER, ContentType.REPO):
            # Target candidate type: if doc is paper, search repos; if repo, search papers
            target_type = ContentType.REPO if doc.content_type == ContentType.PAPER else ContentType.PAPER

            # Retrieve primary chunk embedding of current document
            chunk_res = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc.id, DocumentChunk.chunk_index == 0)
            )
            primary_chunk = chunk_res.scalars().first()

            if primary_chunk and primary_chunk.embedding is not None:
                doc_vec = primary_chunk.embedding
                date_window = timedelta(days=180)
                min_date = (doc.published_at or utc_now()) - date_window
                max_date = (doc.published_at or utc_now()) + date_window

                # Query candidate chunks within date window with cosine distance <= 0.22 (sim >= 0.78)
                sim_res = await db.execute(
                    select(
                        Document,
                        DocumentChunk.embedding.cosine_distance(doc_vec).label("dist"),
                    )
                    .join(DocumentChunk, DocumentChunk.document_id == Document.id)
                    .where(
                        Document.content_type == target_type,
                        Document.id != doc.id,
                        DocumentChunk.chunk_index == 0,
                        DocumentChunk.embedding.is_not(None),
                        Document.published_at >= min_date,
                        Document.published_at <= max_date,
                    )
                    .order_by("dist")
                    .limit(10)
                )
                candidates = sim_res.all()

                for cand_doc, dist in candidates:
                    # Cosine distance: 0.0 means identical (similarity = 1.0)
                    # sim = 1.0 - dist
                    cosine_dist = dist if dist is not None else 1.0
                    sim = round(1.0 - cosine_dist, 4)
                    if sim >= 0.78:
                        # Author / Owner name overlap check
                        authors_a = [a.lower().split()[-1] for a in (doc.authors or []) if len(a.split()) > 0]
                        authors_b = [b.lower().split()[-1] for b in (cand_doc.authors or []) if len(b.split()) > 0]

                        # Also include GitHub repo owner login or repo name
                        if doc.content_type == ContentType.REPO and "/" in doc.canonical_url:
                            repo_owner = doc.canonical_url.rstrip("/").split("/")[-2].lower()
                            authors_a.append(repo_owner)
                        if cand_doc.content_type == ContentType.REPO and "/" in cand_doc.canonical_url:
                            repo_owner = cand_doc.canonical_url.rstrip("/").split("/")[-2].lower()
                            authors_b.append(repo_owner)

                        overlap = set(authors_a).intersection(set(authors_b))
                        if overlap:
                            matched_name = list(overlap)[0]
                            # Assign Repo -> Paper IMPLEMENTS link
                            repo_id = doc.id if doc.content_type == ContentType.REPO else cand_doc.id
                            paper_id = cand_doc.id if doc.content_type == ContentType.REPO else doc.id
                            confidence = min(0.85, max(0.72, sim))

                            created = await cls.upsert_link(
                                db=db,
                                source_id=repo_id,
                                target_id=paper_id,
                                relation_type=RelationType.IMPLEMENTS,
                                confidence_score=confidence,
                                link_method=LinkMethod.SEMANTIC_AUTHOR_MATCH,
                                evidence_snippet=f"Semantic similarity {sim:.2f} + author surname overlap: '{matched_name}'",
                            )
                            if created:
                                links_created += 1

        logger.info("Entity linking complete for document id=%s, created=%d links", doc.id, links_created)
        return links_created

    @classmethod
    async def rebuild_graph_batch(cls, db: AsyncSession, limit: int = 100) -> int:
        """Runs entity linking across up to `limit` processed documents."""
        res = await db.execute(
            select(Document.id)
            .where(Document.processing_status == ProcessingStatus.PROCESSED)
            .order_by(Document.processed_at.desc().nullslast())
            .limit(limit)
        )
        doc_ids = res.scalars().all()
        total_links = 0
        for doc_id in doc_ids:
            links = await cls.link_document_class(db, doc_id)
            total_links += links
        return total_links
