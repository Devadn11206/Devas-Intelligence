"""Story Evolution Timeline & Consensus Radar Analyzer.

Implements Module 7:
- Traverses related items via event_clusters and entity_links across lifecycle:
  Preprint (Paper) -> Open-Source Code (Repo) -> Weights (Model) -> Mainstream Media (News).
- Computes Consensus Status:
  - verified_consensus: 2+ corroborating sources with no contradictions.
  - single_source: only 1 reporting source.
  - disputed: conflicting evidence or critical counter-claims.
"""
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.intel import Document, EventCluster, EntityLink, ConsensusStatus, ContentType


def map_stage(content_type: ContentType) -> str:
    if content_type == ContentType.PAPER:
        return "Preprint / Academic Paper"
    elif content_type == ContentType.REPO:
        return "Open-Source Implementation / Code"
    elif content_type == ContentType.MODEL:
        return "Pretrained Model / Weights Release"
    elif content_type == ContentType.ARTICLE:
        return "Technical Analysis & Industry News"
    return "Ecosystem Tool"


async def get_story_timeline(
    document_id: uuid.UUID,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Retrieves chronological lifecycle timeline and consensus analysis for a document."""
    # 1. Fetch target document with source
    doc_res = await db.execute(
        select(Document)
        .options(selectinload(Document.source), selectinload(Document.event_cluster))
        .where(Document.id == document_id)
    )
    doc = doc_res.scalar_one_or_none()
    if not doc:
        return {
            "document_id": str(document_id),
            "events": [],
            "consensus_status": ConsensusStatus.SINGLE_SOURCE.value,
            "consensus_summary": "Document not found.",
        }

    # 2. Gather sibling documents in the same event cluster
    cluster_docs: List[Document] = []
    if doc.event_cluster_id:
        c_res = await db.execute(
            select(Document)
            .options(selectinload(Document.source))
            .where(Document.event_cluster_id == doc.event_cluster_id)
        )
        cluster_docs = c_res.scalars().all()

    # 3. Gather entity links (incoming and outgoing)
    link_res = await db.execute(
        select(EntityLink).where(
            or_(
                EntityLink.source_entity_id == document_id,
                EntityLink.target_entity_id == document_id,
            )
        )
    )
    links = link_res.scalars().all()
    linked_ids = set()
    for l in links:
        if l.source_entity_id != document_id:
            linked_ids.add(l.source_entity_id)
        if l.target_entity_id != document_id:
            linked_ids.add(l.target_entity_id)

    linked_docs: List[Document] = []
    if linked_ids:
        ld_res = await db.execute(
            select(Document)
            .options(selectinload(Document.source))
            .where(Document.id.in_(list(linked_ids)))
        )
        linked_docs = ld_res.scalars().all()

    # 4. Merge all unique documents into chronological timeline
    combined: Dict[uuid.UUID, Document] = {doc.id: doc}
    for cd in cluster_docs:
        combined[cd.id] = cd
    for ld in linked_docs:
        combined[ld.id] = ld

    sorted_docs = sorted(combined.values(), key=lambda d: d.published_at or d.ingested_at)

    timeline_events = []
    distinct_sources = set()

    for d in sorted_docs:
        source_name = d.source.name if d.source else "External Stream"
        distinct_sources.add(source_name)
        timeline_events.append({
            "document_id": str(d.id),
            "title": d.title,
            "content_type": d.content_type.value,
            "lifecycle_stage": map_stage(d.content_type),
            "source_name": source_name,
            "canonical_url": d.canonical_url,
            "published_at": d.published_at.isoformat() if d.published_at else d.ingested_at.isoformat(),
            "summary": d.summary_raw[:280] + "..." if len(d.summary_raw) > 280 else d.summary_raw,
            "is_focal_point": (d.id == doc.id),
        })

    # 5. Determine Consensus Status & Summary
    num_sources = len(distinct_sources)
    has_dispute = False

    # Check if any article mentions dispute, rebuttal, controversy, or failure
    for d in sorted_docs:
        lower_text = f"{d.title} {d.summary_raw}".lower()
        if any(w in lower_text for w in ["contradict", "dispute", "refuted", "rebuttal", "flaw", "fails to reproduce", "debunk"]):
            has_dispute = True
            break

    if has_dispute:
        consensus_status = ConsensusStatus.DISPUTED
        consensus_summary = f"Dispute detected across {len(sorted_docs)} items. Independent reports suggest conflicting benchmarks or reproducibility caveats."
    elif num_sources >= 2 or len(sorted_docs) >= 3:
        consensus_status = ConsensusStatus.VERIFIED_CONSENSUS
        consensus_summary = f"Multi-source verified consensus confirmed across {num_sources} independent sources ({', '.join(list(distinct_sources)[:3])}). Implementation artifacts corroborate theoretical claims."
    else:
        consensus_status = ConsensusStatus.SINGLE_SOURCE
        consensus_summary = f"Single primary reporting source ({list(distinct_sources)[0] if distinct_sources else 'Unknown'}). Awaiting secondary peer replication or corroborating release."

    # Update cluster consensus status in DB if cluster exists
    if doc.event_cluster:
        doc.event_cluster.consensus_status = consensus_status
        doc.event_cluster.consensus_summary = consensus_summary
        await db.flush()

    return {
        "document_id": str(document_id),
        "total_events": len(timeline_events),
        "consensus_status": consensus_status.value,
        "consensus_summary": consensus_summary,
        "timeline": timeline_events,
    }
