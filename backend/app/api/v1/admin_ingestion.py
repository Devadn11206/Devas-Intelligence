import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models.tenant import User, UserRole
from app.db.models.intel import (
    Source,
    IngestionJob,
    QuarantinedRecord,
    Document,
    DocumentChunk,
    EventCluster,
    ProcessingStatus,
)
from app.api.deps import require_roles, log_audit_event
from app.schemas.intel import (
    SourceCreateRequest,
    SourceUpdateRequest,
    SourceResponse,
    IngestionJobResponse,
    QuarantinedRecordResponse,
    ProcessingBatchTriggerResponse,
    ProcessingStatsResponse,
    LinkingBatchTriggerResponse,
    LinkingStatsResponse,
)
from app.modules.ingestion.service import IngestionService, seed_default_sources
from app.workers.ingestion_tasks import run_source
from app.workers.processing_tasks import process_pending_batch
from app.workers.linking_tasks import rebuild_graph_batch
from app.db.models.intel import EntityLink

router = APIRouter(prefix="/admin", tags=["Admin Ingestion Management"])


@router.get("/sources", response_model=List[SourceResponse])
async def list_sources(
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> List[SourceResponse]:
    """Lists all configured intelligence sources."""
    res = await db.execute(select(Source).order_by(Source.created_at.asc()))
    sources = res.scalars().all()
    # Auto seed if empty
    if not sources:
        await seed_default_sources(db)
        res = await db.execute(select(Source).order_by(Source.created_at.asc()))
        sources = res.scalars().all()
    return sources


@router.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceCreateRequest,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> SourceResponse:
    """Registers a new intelligence source adapter target."""
    existing = await db.execute(
        select(Source).where((Source.name == payload.name) | (Source.slug == payload.slug))
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Source with name '{payload.name}' or slug '{payload.slug}' already exists.",
        )

    source = Source(**payload.dict())
    db.add(source)
    await db.commit()
    await db.refresh(source)

    await log_audit_event(
        db=db,
        action="admin_create_source",
        resource_type="source",
        resource_id=str(source.id),
        actor_user_id=admin_user.id,
        metadata={"slug": source.slug, "category": source.category.value},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return source


@router.patch("/sources/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: uuid.UUID,
    payload: SourceUpdateRequest,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> SourceResponse:
    """Updates configuration, schedule, or activation status of an existing source."""
    res = await db.execute(select(Source).where(Source.id == source_id))
    source = res.scalars().first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(source, field, val)

    await db.commit()
    await db.refresh(source)

    await log_audit_event(
        db=db,
        action="admin_update_source",
        resource_type="source",
        resource_id=str(source.id),
        actor_user_id=admin_user.id,
        metadata={"updated_fields": list(update_data.keys())},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return source


@router.post("/sources/{source_id}/trigger", response_model=IngestionJobResponse)
async def trigger_source_ingestion(
    source_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> IngestionJobResponse:
    """Immediately triggers an on-demand ingestion run for the given source."""
    res = await db.execute(select(Source).where(Source.id == source_id))
    source = res.scalars().first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    await log_audit_event(
        db=db,
        action="admin_trigger_ingestion",
        resource_type="source",
        resource_id=str(source.id),
        actor_user_id=admin_user.id,
        metadata={"slug": source.slug},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    # Run directly via IngestionService so the response immediately reports the execution outcome
    job = await IngestionService.run_source_ingestion(
        db=db,
        source_id=source.id,
        triggered_by=f"manual_admin:{admin_user.email}",
    )

    return IngestionJobResponse(
        id=job.id,
        source_id=job.source_id,
        source_name=source.name,
        celery_task_id=job.celery_task_id,
        status=job.status,
        triggered_by=job.triggered_by,
        records_fetched=job.records_fetched,
        records_inserted=job.records_inserted,
        records_updated=job.records_updated,
        records_quarantined=job.records_quarantined,
        error_summary=job.error_summary,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("/ingestion-jobs", response_model=List[IngestionJobResponse])
async def list_ingestion_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source_id: Optional[uuid.UUID] = None,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> List[IngestionJobResponse]:
    """Lists history and real-time execution status of ingestion jobs."""
    stmt = (
        select(IngestionJob)
        .options(selectinload(IngestionJob.source))
        .order_by(IngestionJob.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if source_id:
        stmt = stmt.where(IngestionJob.source_id == source_id)

    res = await db.execute(stmt)
    jobs = res.scalars().all()

    return [
        IngestionJobResponse(
            id=j.id,
            source_id=j.source_id,
            source_name=j.source.name if j.source else None,
            celery_task_id=j.celery_task_id,
            status=j.status,
            triggered_by=j.triggered_by,
            records_fetched=j.records_fetched,
            records_inserted=j.records_inserted,
            records_updated=j.records_updated,
            records_quarantined=j.records_quarantined,
            error_summary=j.error_summary,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


@router.get("/quarantine", response_model=List[QuarantinedRecordResponse])
async def list_quarantined_records(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source_id: Optional[uuid.UUID] = None,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> List[QuarantinedRecordResponse]:
    """Lists dead-letter quarantined records with validation errors."""
    stmt = select(QuarantinedRecord).order_by(QuarantinedRecord.created_at.desc()).limit(limit).offset(offset)
    if source_id:
        stmt = stmt.where(QuarantinedRecord.source_id == source_id)

    res = await db.execute(stmt)
    records = res.scalars().all()

    return records


@router.post("/processing/trigger-batch", response_model=ProcessingBatchTriggerResponse)
async def trigger_processing_batch(
    limit: int = Query(default=50, ge=1, le=200),
    request: Request = None,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ProcessingBatchTriggerResponse:
    """Enqueues async processing for pending un-indexed documents."""
    # Count pending
    pending_res = await db.execute(
        select(func.count(Document.id)).where(Document.processing_status == ProcessingStatus.RAW_INGESTED)
    )
    pending_count = pending_res.scalar() or 0

    task = None
    if pending_count > 0:
        task = process_pending_batch.delay(limit=limit)

    await log_audit_event(
        db=db,
        action="admin_trigger_processing_batch",
        resource_type="document_processing",
        actor_user_id=admin_user.id,
        metadata={"limit": limit, "pending_count": pending_count, "task_id": task.id if task else None},
        ip_address=request.client.host if request and request.client else None,
    )
    await db.commit()

    return ProcessingBatchTriggerResponse(
        task_id=task.id if task else None,
        pending_count=pending_count,
        enqueued=task is not None,
    )


@router.get("/processing/stats", response_model=ProcessingStatsResponse)
async def get_processing_stats(
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ProcessingStatsResponse:
    """Returns counts of raw_ingested, processed, failed documents, chunks, and clusters."""
    raw_res = await db.execute(
        select(func.count(Document.id)).where(Document.processing_status == ProcessingStatus.RAW_INGESTED)
    )
    processed_res = await db.execute(
        select(func.count(Document.id)).where(Document.processing_status == ProcessingStatus.PROCESSED)
    )
    failed_res = await db.execute(
        select(func.count(Document.id)).where(Document.processing_status == ProcessingStatus.FAILED)
    )
    chunk_res = await db.execute(select(func.count(DocumentChunk.id)))
    cluster_res = await db.execute(select(func.count(EventCluster.id)))

    return ProcessingStatsResponse(
        raw_ingested_count=raw_res.scalar() or 0,
        processed_count=processed_res.scalar() or 0,
        failed_count=failed_res.scalar() or 0,
        total_chunks=chunk_res.scalar() or 0,
        total_clusters=cluster_res.scalar() or 0,
    )


# ==============================================================================
# Phase 4: Entity Linking Admin Endpoints
# ==============================================================================

@router.post("/linking/rebuild", response_model=LinkingBatchTriggerResponse)
async def trigger_rebuild_linking(
    limit: int = Query(default=100, ge=1, le=500),
    request: Request = None,
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> LinkingBatchTriggerResponse:
    """Triggers asynchronous Celery task to re-run 3-pass entity linking across processed documents."""
    task = rebuild_graph_batch.delay(limit=limit)

    await log_audit_event(
        db=db,
        action="admin_trigger_linking_rebuild",
        resource_type="entity_linking",
        actor_user_id=admin_user.id,
        metadata={"limit": limit, "task_id": task.id if task else None},
        ip_address=request.client.host if request and request.client else None,
    )
    await db.commit()

    return LinkingBatchTriggerResponse(
        task_id=task.id if task else None,
        enqueued=task is not None,
        batch_size=limit,
    )


@router.get("/linking/stats", response_model=LinkingStatsResponse)
async def get_linking_stats(
    admin_user: User = Depends(require_roles(UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> LinkingStatsResponse:
    """Returns total count and breakdowns by relation_type and link_method."""
    total_res = await db.execute(select(func.count(EntityLink.id)))
    total_links = total_res.scalar() or 0

    rel_res = await db.execute(
        select(EntityLink.relation_type, func.count(EntityLink.id)).group_by(EntityLink.relation_type)
    )
    by_relation_type = {r.value if hasattr(r, 'value') else str(r): count for r, count in rel_res.all()}

    method_res = await db.execute(
        select(EntityLink.link_method, func.count(EntityLink.id)).group_by(EntityLink.link_method)
    )
    by_link_method = {m.value if hasattr(m, 'value') else str(m): count for m, count in method_res.all()}

    return LinkingStatsResponse(
        total_links=total_links,
        by_relation_type=by_relation_type,
        by_link_method=by_link_method,
    )
