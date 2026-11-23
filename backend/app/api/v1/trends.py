import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.intel import TrendSnapshot, SignalClassification
from app.modules.trends.calculator import TrendService
from app.modules.trends.timeline import get_story_timeline
from app.schemas.intel import (
    TrendsOverviewResponse,
    TrendSnapshotItem,
    StoryTimelineResponse,
)

router = APIRouter(prefix="/trends", tags=["Trend Velocity & Story Evolution"])


@router.get("/overview", response_model=TrendsOverviewResponse)
async def get_trends_overview(
    domain: Optional[str] = None,
    force_recompute: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> TrendsOverviewResponse:
    """Returns aggregated trend velocity, hype-vs-substance ratio, and momentum classifications."""
    # Check if snapshots exist
    stmt = select(TrendSnapshot).order_by(TrendSnapshot.velocity_growth_pct.desc())
    if domain and domain.lower() != "all":
        stmt = stmt.where(TrendSnapshot.domain.ilike(f"%{domain}%"))

    res = await db.execute(stmt)
    snapshots = res.scalars().all()

    if not snapshots or force_recompute:
        # Compute fresh snapshots from current data
        await TrendService.compute_daily_snapshots(db)
        res = await db.execute(stmt)
        snapshots = res.scalars().all()

    breakthrough = [s for s in snapshots if s.signal_classification == SignalClassification.BREAKTHROUGH_MOMENTUM]
    hype = [s for s in snapshots if s.signal_classification == SignalClassification.HYPE_SPIKE]
    steady = [s for s in snapshots if s.signal_classification == SignalClassification.STEADY_ADOPTION]
    cooling = [s for s in snapshots if s.signal_classification == SignalClassification.COOLING]

    return TrendsOverviewResponse(
        computed_at=datetime.now(timezone.utc),
        total_tracked_topics=len(snapshots),
        signal_counts={
            "breakthrough_momentum": len(breakthrough),
            "hype_spikes": len(hype),
            "steady_adoption": len(steady),
            "cooling": len(cooling),
        },
        breakthrough_momentum=breakthrough[:10],
        hype_spikes=hype[:10],
        steady_adoption=steady[:10],
        cooling=cooling[:10],
        all_snapshots=snapshots[:50],
    )


@router.post("/recompute", response_model=TrendsOverviewResponse)
async def recompute_trends(
    domain: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> TrendsOverviewResponse:
    """Immediately recalculates live 7-day topic velocity snapshots from documents + entity links."""
    await TrendService.compute_daily_snapshots(db)
    
    stmt = select(TrendSnapshot).order_by(TrendSnapshot.velocity_growth_pct.desc())
    if domain and domain.lower() != "all":
        stmt = stmt.where(TrendSnapshot.domain.ilike(f"%{domain}%"))

    res = await db.execute(stmt)
    snapshots = res.scalars().all()

    breakthrough = [s for s in snapshots if s.signal_classification == SignalClassification.BREAKTHROUGH_MOMENTUM]
    hype = [s for s in snapshots if s.signal_classification == SignalClassification.HYPE_SPIKE]
    steady = [s for s in snapshots if s.signal_classification == SignalClassification.STEADY_ADOPTION]
    cooling = [s for s in snapshots if s.signal_classification == SignalClassification.COOLING]

    return TrendsOverviewResponse(
        computed_at=datetime.now(timezone.utc),
        total_tracked_topics=len(snapshots),
        signal_counts={
            "breakthrough_momentum": len(breakthrough),
            "hype_spikes": len(hype),
            "steady_adoption": len(steady),
            "cooling": len(cooling),
        },
        breakthrough_momentum=breakthrough[:10],
        hype_spikes=hype[:10],
        steady_adoption=steady[:10],
        cooling=cooling[:10],
        all_snapshots=snapshots[:50],
    )


@router.get("/documents/{document_id}/timeline", response_model=StoryTimelineResponse)
async def get_document_story_timeline(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StoryTimelineResponse:
    """Returns chronological story evolution timeline across preprint, code, model, and news with consensus status."""
    timeline_data = await get_story_timeline(document_id, db)
    return StoryTimelineResponse(
        document_id=timeline_data["document_id"],
        total_events=timeline_data["total_events"],
        consensus_status=timeline_data["consensus_status"],
        consensus_summary=timeline_data["consensus_summary"],
        timeline=timeline_data["timeline"],
    )
