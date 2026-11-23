"""Trend Velocity, Hype-vs-Substance Analytics & Snapshot Calculator.

Implements PRD Module 7:
- Rolling 7-day velocity and growth percentage calculation.
- Counts real repository activity from both direct repo tags AND linked repositories.
- Domain-accurate classification (Healthcare & Biotech, Audio & Entertainment, Space & Physics, AI & Software).
- hype_to_substance_ratio = news_count_7d / max(1, paper_count_7d + repo_count_7d)
- Signal Classification:
  - breakthrough_momentum: high paper/repo velocity + positive growth
  - hype_spike: high news ratio with low peer-reviewed/code backing (ratio > 2.0)
  - steady_adoption: sustained moderate velocity with healthy repo/paper support
  - cooling: negative growth compared to previous window
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.intel import Document, ContentType, TrendSnapshot, SignalClassification, EntityLink

logger = logging.getLogger(__name__)


def classify_topic_domain(topic: str) -> str:
    """Classifies topic tags into their accurate technical domain."""
    t = topic.lower()

    # 1. Healthcare & Biotech
    if any(k in t for k in [
        "q-bio", "medical", "clinical", "fda", "biotech", "health",
        "cryo-em", "genom", "med-ph", "cancer", "drug", "pharma", "disease", "bio"
    ]):
        return "Healthcare & Biotech"

    # 2. Audio & Entertainment
    if any(k in t for k in [
        "eess.as", "eess.sp", "audio", "speech", "whisper", "music",
        "sound", "acoustic", "voice", "asr", "wav2vec", "image-to-video",
        "comfyui", "game", "gaming"
    ]):
        return "Audio & Entertainment"

    # 3. Space & Physics
    if any(k in t for k in [
        "physics", "cond-mat", "space", "astro", "quantum", "pinn",
        "partial differential equations", "neural operator", "fno", "sciml",
        "fluid", "navier-stokes", "nasa", "mars", "orbit", "satellite", "astronomy"
    ]):
        return "Space & Physics"

    # 4. AI & Software (cs.*, stat.ml, llm, etc.)
    return "AI & Software"


def calculate_signal(
    paper_count: int,
    repo_count: int,
    news_count: int,
    velocity_growth_pct: float,
    hype_ratio: float,
) -> SignalClassification:
    """Classifies a trend into one of 4 PRD signal states."""
    substance = paper_count + repo_count

    # 1. Hype Spike: News/blog mentions dominate without solid paper/repo backing
    if hype_ratio >= 2.0 and news_count >= 2:
        return SignalClassification.HYPE_SPIKE

    # 2. Cooling: Negative velocity growth compared to previous 7 days
    if velocity_growth_pct < -15.0:
        return SignalClassification.COOLING

    # 3. Breakthrough Momentum: Strong paper/repo activity and robust growth
    if substance >= 3 and velocity_growth_pct >= 20.0:
        return SignalClassification.BREAKTHROUGH_MOMENTUM

    if substance >= 5:
        return SignalClassification.BREAKTHROUGH_MOMENTUM

    # 4. Steady Adoption: Balanced and sustained momentum
    return SignalClassification.STEADY_ADOPTION


class TrendService:
    """Service to compute rolling velocity, hype-vs-substance snapshots, and trend radar."""

    @staticmethod
    async def compute_daily_snapshots(
        db: AsyncSession,
        target_date: Optional[datetime] = None,
    ) -> List[TrendSnapshot]:
        """Calculates rolling 7-day activity metrics for all distinct topics in DEVA."""
        if target_date is None:
            target_date = datetime.now(timezone.utc)

        window_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        window_start = (window_end - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        prior_start = (window_start - timedelta(days=7))

        # 1. Preload Paper <-> Repo Entity Links to count linked repositories accurately
        link_stmt = (
            select(EntityLink.source_entity_id, EntityLink.target_entity_id)
        )
        links_res = await db.execute(link_stmt)
        links_rows = links_res.all()

        # Build bidirectional document adjacency map
        doc_neighbors: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        for s_id, t_id in links_rows:
            doc_neighbors.setdefault(s_id, set()).add(t_id)
            doc_neighbors.setdefault(t_id, set()).add(s_id)

        # 2. Query all documents in the database
        stmt = select(
            Document.id,
            Document.tags,
            Document.content_type,
            Document.published_at,
            Document.metadata_,
        )
        res = await db.execute(stmt)
        doc_rows = res.all()

        # Map document id to ContentType and published_at
        doc_type_map: Dict[uuid.UUID, ContentType] = {}
        for d_id, tags, ctype, pub_at, meta in doc_rows:
            doc_type_map[d_id] = ctype

        # Track linked repos per document id
        doc_linked_repo_count: Dict[uuid.UUID, int] = {}
        for d_id, neighbors in doc_neighbors.items():
            repo_neighbors = sum(1 for n_id in neighbors if doc_type_map.get(n_id) == ContentType.REPO)
            doc_linked_repo_count[d_id] = repo_neighbors

        current_metrics: Dict[str, Dict[str, Any]] = {}
        prior_counts: Dict[str, int] = {}

        for d_id, tags, ctype, pub_at, meta in doc_rows:
            if not tags:
                continue

            # Determine whether document falls into rolling window or prior window
            # If doc has published_at, use it; otherwise fallback to current window
            is_current = True
            is_prior = False
            if pub_at:
                is_current = pub_at >= window_start
                is_prior = (pub_at >= prior_start and pub_at < window_start)

            # Connected repos count for this document
            linked_repo_num = doc_linked_repo_count.get(d_id, 0)

            for tag in tags:
                clean_tag = tag.strip().lower()
                if not clean_tag or len(clean_tag) < 2 or ":" in clean_tag:
                    continue

                domain = classify_topic_domain(clean_tag)

                if is_current:
                    if clean_tag not in current_metrics:
                        current_metrics[clean_tag] = {
                            "domain": domain,
                            "papers": 0,
                            "repos": 0,
                            "news": 0,
                        }

                    if ctype == ContentType.PAPER:
                        current_metrics[clean_tag]["papers"] += 1
                        # If this paper has connected repos in the knowledge graph, accumulate repo count
                        current_metrics[clean_tag]["repos"] += linked_repo_num
                    elif ctype == ContentType.REPO:
                        current_metrics[clean_tag]["repos"] += 1
                    elif ctype in (ContentType.ARTICLE, ContentType.MODEL, ContentType.TOOL):
                        current_metrics[clean_tag]["news"] += 1

                elif is_prior:
                    prior_counts[clean_tag] = prior_counts.get(clean_tag, 0) + 1

        snapshots: List[TrendSnapshot] = []
        snap_date = target_date.date()
        snap_datetime = datetime(snap_date.year, snap_date.month, snap_date.day)

        for topic, counts in current_metrics.items():
            papers = counts["papers"]
            repos = counts["repos"]
            news = counts["news"]
            total_current = papers + repos + news
            total_prior = prior_counts.get(topic, 0)

            # Growth percentage vs prior window
            if total_prior > 0:
                growth_pct = round(((total_current - total_prior) / float(total_prior)) * 100.0, 2)
            else:
                growth_pct = round(total_current * 50.0, 2) if total_current > 0 else 0.0

            # Hype to substance ratio: news / max(1, papers + repos)
            substance = papers + repos
            hype_ratio = round(news / float(max(1, substance)), 2)

            signal = calculate_signal(
                paper_count=papers,
                repo_count=repos,
                news_count=news,
                velocity_growth_pct=growth_pct,
                hype_ratio=hype_ratio,
            )

            # Check if snapshot already exists for (topic_tag, snap_datetime)
            existing_res = await db.execute(
                select(TrendSnapshot).where(
                    TrendSnapshot.topic_tag == topic,
                    TrendSnapshot.window_date == snap_datetime,
                )
            )
            snapshot = existing_res.scalar_one_or_none()

            if not snapshot:
                snapshot = TrendSnapshot(
                    id=uuid.uuid4(),
                    topic_tag=topic,
                    domain=counts["domain"],
                    window_date=snap_datetime,
                    paper_count_7d=papers,
                    repo_count_7d=repos,
                    news_count_7d=news,
                    velocity_growth_pct=growth_pct,
                    hype_to_substance_ratio=hype_ratio,
                    signal_classification=signal,
                )
                db.add(snapshot)
            else:
                snapshot.domain = counts["domain"]
                snapshot.paper_count_7d = papers
                snapshot.repo_count_7d = repos
                snapshot.news_count_7d = news
                snapshot.velocity_growth_pct = growth_pct
                snapshot.hype_to_substance_ratio = hype_ratio
                snapshot.signal_classification = signal

            snapshots.append(snapshot)

        await db.commit()
        return snapshots
