import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, func, or_, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models.intel import (
    Document,
    DocumentChunk,
    EventCluster,
    Source,
    ContentType,
    ProcessingStatus,
    EntityLink,
)
from app.schemas.intel import (
    DocumentResponse,
    IntelFeedCardResponse,
    CorroboratingSource,
    DocumentDetailResponse,
    EntityLinkResponse,
    GraphNode,
    GraphEdge,
    KnowledgeGraphResponse,
)
from app.modules.retrieval.comparator import (
    ComparisonService,
    ComparisonRequest,
    ComparisonMatrixResponse,
)

router = APIRouter(prefix="/intel", tags=["Intelligence Documents & Live Feeds"])


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    content_type: Optional[ContentType] = None,
    source_id: Optional[uuid.UUID] = None,
    tag: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """Lists raw or processed documents with optional filters."""
    stmt = select(Document).order_by(Document.published_at.desc()).limit(limit).offset(offset)

    if content_type:
        stmt = stmt.where(Document.content_type == content_type)
    if source_id:
        stmt = stmt.where(Document.source_id == source_id)
    if tag:
        stmt = stmt.where(Document.tags.contains([tag]))

    res = await db.execute(stmt)
    docs = res.scalars().all()

    return [
        DocumentResponse(
            id=d.id,
            source_id=d.source_id,
            event_cluster_id=d.event_cluster_id,
            content_type=d.content_type,
            external_id=d.external_id,
            canonical_url=d.canonical_url,
            content_hash=d.content_hash,
            title=d.title,
            summary_raw=d.summary_raw,
            summary_ai=d.summary_ai,
            content_raw=d.content_raw,
            authors=d.authors or [],
            tags=d.tags or [],
            metadata=d.metadata_ or {},
            processing_status=d.processing_status,
            processing_error=d.processing_error,
            published_at=d.published_at,
            processed_at=d.processed_at,
            ingested_at=d.ingested_at,
            updated_at=d.updated_at,
        )
        for d in docs
    ]


@router.get("/feed", response_model=List[IntelFeedCardResponse])
async def get_intelligence_feed(
    response: Response,
    content_type: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
    domain: Optional[str] = None,
    for_you: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[IntelFeedCardResponse]:
    """Returns clustered intelligence feed items with optional for_you personalization, multi-content-type and domain filters."""
    # We query documents joined with Source and EventCluster
    # Grouping/deduping by event_cluster_id (or document id if event_cluster_id is null)
    stmt = (
        select(Document)
        .outerjoin(Source, Document.source_id == Source.id)
        .options(selectinload(Document.source), selectinload(Document.event_cluster))
        .order_by(Document.published_at.desc())
    )

    if content_type:
        raw_types = [t.strip().lower() for t in content_type.split(",") if t.strip()]
        matched_enums = []
        for raw in raw_types:
            for enum_val in ContentType:
                if enum_val.value.lower() == raw or enum_val.name.lower() == raw:
                    matched_enums.append(enum_val)
        if matched_enums:
            stmt = stmt.where(Document.content_type.in_(matched_enums))

    # Unified tag filter: case-insensitive match against tags JSONB/array
    if tag and tag.strip():
        tag_val = tag.strip()
        stmt = stmt.where(cast(Document.tags, String).ilike(f"%{tag_val}%"))

    # Unified search / q parameter: matches title OR summary_raw OR tags
    query_term = (q or search or "").strip()
    if query_term:
        query_pattern = f"%{query_term}%"
        stmt = stmt.where(
            or_(
                Document.title.ilike(query_pattern),
                Document.summary_raw.ilike(query_pattern),
                cast(Document.tags, String).ilike(query_pattern),
            )
        )

    # Domain filtering across tags, source category, source slug, and domain keywords
    if domain and domain.lower() != "all":
        dom = domain.lower()
        domain_patterns = {
            "ai": [
                "ai", "llm", "neural", "deep learning", "machine learning", "diffusion", "inference",
                "vision", "nlp", "cs.lg", "cs.ai", "cs.cv", "cs.cl", "pytorch", "transformer", "hugging face"
            ],
            "healthcare": [
                "health", "biotech", "medical", "drug", "clinical", "genomic", "bio", "cancer", "patient",
                "fda", "q-bio", "therapy", "pharma", "disease", "duchenne", "dystrophy", "cryo-em"
            ],
            "audio": [
                "music", "audio", "sound", "acoustic", "speech", "synth", "whisper", "voice", "asr",
                "wav2vec", "speaker", "recording", "synthesizer"
            ],
            "gaming": [
                "game", "gaming", "graphics", "steam", "playstation", "xbox", "nintendo", "valve",
                "render", "entertainment", "culture"
            ],
            "space": [
                "spacecraft", "nasa", "astrophysics", "physics", "quantum", "climate", "energy", "planet",
                "astronomy", "spacex", "orbit", "pde", "sciml", "navier-stokes", "fluid dynamics", "aerospace"
            ],
        }.get(dom, [dom])

        domain_sources = {
            "ai": ["arxiv-efficient-llm-systems", "github-opensource-llm-inference", "hf-top-models", "pytorch-engineering-blog", "huggingface-engineering-blog"],
            "healthcare": ["stat-news-biotech"],
            "audio": ["musictech-audio-ai"],
            "gaming": ["arstechnica-gaming-tech"],
            "space": ["nasa-space-science", "arxiv-sciml-pinns", "github-sciml-pinns", "semantic-scholar-sciml"],
        }.get(dom, [])

        domain_filters = []
        for kw in domain_patterns:
            kw_pat = f"%{kw}%"
            domain_filters.append(Document.title.ilike(kw_pat))
            domain_filters.append(Document.tags.contains([kw]))
        if domain_sources:
            domain_filters.append(Source.slug.in_(domain_sources))
        stmt = stmt.where(or_(*domain_filters))

    # Fetch a batch to aggregate clusters
    stmt = stmt.limit(limit * 3).offset(offset)
    res = await db.execute(stmt)
    docs = res.scalars().all()

    # Cluster grouping
    seen_clusters: set[uuid.UUID] = set()
    cards: List[IntelFeedCardResponse] = []

    for doc in docs:
        cluster = doc.event_cluster
        if cluster:
            if cluster.id in seen_clusters:
                continue
            seen_clusters.add(cluster.id)

            # Retrieve all documents in this cluster to build corroborating sources
            cluster_docs_res = await db.execute(
                select(Document)
                .options(selectinload(Document.source))
                .where(Document.event_cluster_id == cluster.id)
                .order_by(Document.published_at.asc())
            )
            cluster_docs = cluster_docs_res.scalars().all()

            # Corroborating sources list
            corroborating = [
                CorroboratingSource(
                    document_id=cd.id,
                    source_name=cd.source.name if cd.source else "Source",
                    canonical_url=cd.canonical_url,
                    published_at=cd.published_at,
                )
                for cd in cluster_docs
            ]

            # Compute linked repos and papers count for this cluster/doc
            outgoing_links_res = await db.execute(
                select(EntityLink).options(selectinload(EntityLink.target_entity))
                .where(EntityLink.source_entity_id == doc.id)
            )
            incoming_links_res = await db.execute(
                select(EntityLink).options(selectinload(EntityLink.source_entity))
                .where(EntityLink.target_entity_id == doc.id)
            )
            all_links = outgoing_links_res.scalars().all() + incoming_links_res.scalars().all()
            linked_repos = 0
            linked_papers = 0
            for l in all_links:
                other = l.target_entity if l.source_entity_id == doc.id else l.source_entity
                if other:
                    if other.content_type == ContentType.REPO:
                        linked_repos += 1
                    elif other.content_type == ContentType.PAPER:
                        linked_papers += 1

            card = IntelFeedCardResponse(
                id=doc.id,
                event_cluster_id=cluster.id,
                primary_document_id=doc.id,
                title=cluster.canonical_title or doc.title,
                content_type=doc.content_type,
                summary_raw=doc.summary_raw,
                summary_ai=doc.summary_ai,
                authors=doc.authors or [],
                tags=doc.tags or [],
                metadata=doc.metadata_ or {},
                published_at=doc.published_at,
                source_name=doc.source.name if doc.source else "Unknown",
                source_category=doc.source.category.value if doc.source else "tech_news",
                canonical_url=doc.canonical_url,
                document_count=cluster.document_count,
                corroborating_sources=corroborating,
                consensus_status=cluster.consensus_status,
                consensus_summary=cluster.consensus_summary,
                linked_repos_count=linked_repos,
                linked_papers_count=linked_papers,
            )
            cards.append(card)
        else:
            # Standalone document
            outgoing_links_res = await db.execute(
                select(EntityLink).options(selectinload(EntityLink.target_entity))
                .where(EntityLink.source_entity_id == doc.id)
            )
            incoming_links_res = await db.execute(
                select(EntityLink).options(selectinload(EntityLink.source_entity))
                .where(EntityLink.target_entity_id == doc.id)
            )
            all_links = outgoing_links_res.scalars().all() + incoming_links_res.scalars().all()
            linked_repos = 0
            linked_papers = 0
            for l in all_links:
                other = l.target_entity if l.source_entity_id == doc.id else l.source_entity
                if other:
                    if other.content_type == ContentType.REPO:
                        linked_repos += 1
                    elif other.content_type == ContentType.PAPER:
                        linked_papers += 1

            card = IntelFeedCardResponse(
                id=doc.id,
                event_cluster_id=None,
                primary_document_id=doc.id,
                title=doc.title,
                content_type=doc.content_type,
                summary_raw=doc.summary_raw,
                summary_ai=doc.summary_ai,
                authors=doc.authors or [],
                tags=doc.tags or [],
                metadata=doc.metadata_ or {},
                published_at=doc.published_at,
                source_name=doc.source.name if doc.source else "Unknown",
                source_category=doc.source.category.value if doc.source else "tech_news",
                canonical_url=doc.canonical_url,
                document_count=1,
                corroborating_sources=[],
                linked_repos_count=linked_repos,
                linked_papers_count=linked_papers,
            )
            cards.append(card)

        if len(cards) >= limit:
            break

    # Response headers with total documents
    total_docs_res = await db.execute(select(func.count(Document.id)))
    total_docs_count = total_docs_res.scalar() or 0
    response.headers["X-Total-Count"] = str(total_docs_count)

    return cards


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_details(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Returns detailed document analysis, separating raw vs AI fields, chunk count, and cluster siblings."""
    stmt = (
        select(Document)
        .options(selectinload(Document.source), selectinload(Document.event_cluster))
        .where(Document.id == document_id)
    )
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Chunk count
    chunk_count_res = await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc.id)
    )
    chunk_count = chunk_count_res.scalar() or 0

    # Cluster siblings
    siblings: List[Document] = []
    cluster_doc_count = 1
    if doc.event_cluster_id:
        cluster_siblings_res = await db.execute(
            select(Document)
            .where(Document.event_cluster_id == doc.event_cluster_id, Document.id != doc.id)
            .order_by(Document.published_at.desc())
        )
        siblings = cluster_siblings_res.scalars().all()
        if doc.event_cluster:
            cluster_doc_count = doc.event_cluster.document_count

    # Ensure detailed_briefing exists and is genuinely comprehensive (>= 260 words)
    current_brief = (doc.summary_ai or {}).get("detailed_briefing", "")
    if not current_brief or len(current_brief.split()) < 260:
        try:
            from app.modules.processing.extractor import StructuredExtractor
            extractor = StructuredExtractor()
            new_ai, new_tags = extractor._heuristic_fallback(doc)
            existing_ai = dict(doc.summary_ai or {})
            existing_ai.update(new_ai)
            doc.summary_ai = existing_ai
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(doc, "summary_ai")
            await db.commit()
            await db.refresh(doc)
        except Exception as e:
            import logging
            logging.getLogger("intel.api").error("Failed to generate on-demand briefing: %s", e)

    doc_response = DocumentResponse(
        id=doc.id,
        source_id=doc.source_id,
        event_cluster_id=doc.event_cluster_id,
        content_type=doc.content_type,
        external_id=doc.external_id,
        canonical_url=doc.canonical_url,
        content_hash=doc.content_hash,
        title=doc.title,
        summary_raw=doc.summary_raw,
        summary_ai=doc.summary_ai,
        content_raw=doc.content_raw,
        authors=doc.authors or [],
        tags=doc.tags or [],
        metadata=doc.metadata_ or {},
        processing_status=doc.processing_status,
        processing_error=doc.processing_error,
        published_at=doc.published_at,
        processed_at=doc.processed_at,
        ingested_at=doc.ingested_at,
        updated_at=doc.updated_at,
    )

    sibling_responses = [
        DocumentResponse(
            id=s.id,
            source_id=s.source_id,
            event_cluster_id=s.event_cluster_id,
            content_type=s.content_type,
            external_id=s.external_id,
            canonical_url=s.canonical_url,
            content_hash=s.content_hash,
            title=s.title,
            summary_raw=s.summary_raw,
            summary_ai=s.summary_ai,
            content_raw=s.content_raw,
            authors=s.authors or [],
            tags=s.tags or [],
            metadata=s.metadata_ or {},
            processing_status=s.processing_status,
            processing_error=s.processing_error,
            published_at=s.published_at,
            processed_at=s.processed_at,
            ingested_at=s.ingested_at,
            updated_at=s.updated_at,
        )
        for s in siblings
    ]

    return DocumentDetailResponse(
        document=doc_response,
        source_name=doc.source.name if doc.source else "Source",
        chunk_count=chunk_count,
        cluster_document_count=cluster_doc_count,
        cluster_siblings=sibling_responses,
    )


# ==============================================================================
# Phase 4: Entity Links & Knowledge Graph Subgraph Endpoints
# ==============================================================================

@router.get("/documents/{document_id}/links", response_model=List[EntityLinkResponse])
async def get_document_links(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[EntityLinkResponse]:
    """Returns all outgoing and incoming links for a document with linked document previews."""
    # Outgoing links
    out_stmt = (
        select(EntityLink)
        .options(selectinload(EntityLink.target_entity))
        .where(EntityLink.source_entity_id == document_id)
        .order_by(EntityLink.confidence_score.desc())
    )
    out_res = await db.execute(out_stmt)
    outgoing_links = out_res.scalars().all()

    # Incoming links
    in_stmt = (
        select(EntityLink)
        .options(selectinload(EntityLink.source_entity))
        .where(EntityLink.target_entity_id == document_id)
        .order_by(EntityLink.confidence_score.desc())
    )
    in_res = await db.execute(in_stmt)
    incoming_links = in_res.scalars().all()

    result: List[EntityLinkResponse] = []

    def to_doc_response(d: Document) -> DocumentResponse:
        return DocumentResponse(
            id=d.id,
            source_id=d.source_id,
            event_cluster_id=d.event_cluster_id,
            content_type=d.content_type,
            external_id=d.external_id,
            canonical_url=d.canonical_url,
            content_hash=d.content_hash,
            title=d.title,
            summary_raw=d.summary_raw,
            summary_ai=d.summary_ai,
            content_raw=d.content_raw,
            authors=d.authors or [],
            tags=d.tags or [],
            metadata=d.metadata_ or {},
            processing_status=d.processing_status,
            processing_error=d.processing_error,
            published_at=d.published_at,
            processed_at=d.processed_at,
            ingested_at=d.ingested_at,
            updated_at=d.updated_at,
        )

    for l in outgoing_links:
        if l.target_entity:
            result.append(
                EntityLinkResponse(
                    id=l.id,
                    source_entity_id=l.source_entity_id,
                    target_entity_id=l.target_entity_id,
                    relation_type=l.relation_type,
                    confidence_score=l.confidence_score,
                    link_method=l.link_method,
                    evidence_snippet=l.evidence_snippet,
                    direction="outgoing",
                    linked_document=to_doc_response(l.target_entity),
                    created_at=l.created_at,
                )
            )

    for l in incoming_links:
        if l.source_entity:
            result.append(
                EntityLinkResponse(
                    id=l.id,
                    source_entity_id=l.source_entity_id,
                    target_entity_id=l.target_entity_id,
                    relation_type=l.relation_type,
                    confidence_score=l.confidence_score,
                    link_method=l.link_method,
                    evidence_snippet=l.evidence_snippet,
                    direction="incoming",
                    linked_document=to_doc_response(l.source_entity),
                    created_at=l.created_at,
                )
            )

    return result


@router.get("/documents/{document_id}/graph", response_model=KnowledgeGraphResponse)
async def get_document_subgraph(
    document_id: uuid.UUID,
    depth: int = Query(default=2, ge=1, le=3),
    min_confidence: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeGraphResponse:
    """Traverses 1-3 hops from root document to assemble a subgraph of nodes and directed edges.
    Caps Hop 1 to top 10 highest-confidence neighbors and Hop 2 to top 8 neighbors to prevent visual overlap.
    """
    root_res = await db.execute(
        select(Document).options(selectinload(Document.source)).where(Document.id == document_id)
    )
    root_doc = root_res.scalars().first()
    if not root_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Root document not found")

    visited_node_ids: set[uuid.UUID] = {root_doc.id}
    nodes_map: dict[uuid.UUID, Document] = {root_doc.id: root_doc}
    collected_edges: dict[uuid.UUID, EntityLink] = {}

    current_frontier: set[uuid.UUID] = {root_doc.id}

    for hop in range(depth):
        if not current_frontier:
            break
        
        # Determine cap for this hop: Hop 0 (first traversal) -> 10, subsequent -> 8
        hop_cap = 10 if hop == 0 else 8

        # Find all outgoing and incoming links for current_frontier ordered by confidence desc
        link_query = (
            select(EntityLink)
            .options(
                selectinload(EntityLink.source_entity).selectinload(Document.source),
                selectinload(EntityLink.target_entity).selectinload(Document.source),
            )
            .where(
                or_(
                    EntityLink.source_entity_id.in_(current_frontier),
                    EntityLink.target_entity_id.in_(current_frontier),
                )
            )
        )
        if min_confidence is not None:
            link_query = link_query.where(EntityLink.confidence_score >= min_confidence)

        link_query = link_query.order_by(EntityLink.confidence_score.desc())
        links_res = await db.execute(link_query)
        links = links_res.scalars().all()

        next_frontier: set[uuid.UUID] = set()
        added_in_hop = 0

        for link in links:
            source_doc = link.source_entity
            target_doc = link.target_entity
            
            # Identify other doc relative to current frontier
            other_doc = None
            if link.source_entity_id in current_frontier and target_doc:
                other_doc = target_doc
            elif link.target_entity_id in current_frontier and source_doc:
                other_doc = source_doc

            if other_doc:
                if other_doc.id not in visited_node_ids:
                    if added_in_hop >= hop_cap:
                        continue
                    visited_node_ids.add(other_doc.id)
                    nodes_map[other_doc.id] = other_doc
                    next_frontier.add(other_doc.id)
                    added_in_hop += 1
                collected_edges[link.id] = link
            elif link.source_entity_id in visited_node_ids and link.target_entity_id in visited_node_ids:
                collected_edges[link.id] = link

        current_frontier = next_frontier

    graph_nodes = [
        GraphNode(
            id=str(d.id),
            title=d.title,
            content_type=d.content_type,
            canonical_url=d.canonical_url,
            source_name=d.source.name if d.source else None,
            published_at=d.published_at,
            is_root=(d.id == root_doc.id),
        )
        for d in nodes_map.values()
    ]

    graph_edges = [
        GraphEdge(
            id=str(e.id),
            source=str(e.source_entity_id),
            target=str(e.target_entity_id),
            relation_type=e.relation_type,
            confidence_score=e.confidence_score,
            link_method=e.link_method,
            evidence_snippet=e.evidence_snippet,
        )
        for e in collected_edges.values()
    ]

    return KnowledgeGraphResponse(
        root_document_id=root_doc.id,
        nodes=graph_nodes,
        edges=graph_edges,
    )


# ==============================================================================
# Phase 8: Multi-Item Side-by-Side Comparison Matrix
# ==============================================================================

@router.post("/compare", response_model=ComparisonMatrixResponse)
async def compare_documents_endpoint(
    req: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> ComparisonMatrixResponse:
    """Performs side-by-side comparative matrix synthesis across 2 to 4 documents."""
    return await ComparisonService.compare_documents(req.document_ids, db)

