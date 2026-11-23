import asyncio
import uuid
import structlog
from celery import shared_task
from sqlalchemy import select, or_

from app.workers.celery_app import celery_app
from app.db.session import async_session_factory
from app.db.models.intel import Source
from app.modules.ingestion.service import IngestionService, utc_now

logger = structlog.get_logger(__name__)


@celery_app.task(name="ingestion.run_source", queue="ingestion", acks_late=True)
def run_source(source_id: str, triggered_by: str = "scheduler") -> dict:
    """Celery task executing source ingestion in an asyncio loop."""
    logger.info("Executing ingestion.run_source task", source_id=source_id, triggered_by=triggered_by)

    async def _execute() -> dict:
        async with async_session_factory() as session:
            job = await IngestionService.run_source_ingestion(
                db=session,
                source_id=uuid.UUID(source_id),
                triggered_by=triggered_by,
            )
            # If new or updated records were ingested, automatically trigger processing batch
            if job.records_inserted > 0 or job.records_updated > 0:
                try:
                    from app.workers.processing_tasks import process_pending_batch
                    process_pending_batch.delay(limit=50)
                except Exception as e:
                    logger.warning("Failed to auto-enqueue processing batch", error=str(e))

            return {
                "job_id": str(job.id),
                "status": job.status.value,
                "records_fetched": job.records_fetched,
                "records_inserted": job.records_inserted,
                "records_updated": job.records_updated,
                "records_quarantined": job.records_quarantined,
            }

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_execute())
    finally:
        loop.close()


@celery_app.task(name="ingestion.schedule_due_sources", queue="ingestion")
def schedule_due_sources() -> dict:
    """Dispatches ingestion jobs for all active sources that are due for a refresh."""
    logger.info("Evaluating due sources for scheduled ingestion")

    async def _find_and_dispatch() -> list:
        dispatched = []
        async with async_session_factory() as session:
            res = await session.execute(
                select(Source).where(Source.is_enabled == True)
            )
            sources = res.scalars().all()
            now = utc_now()

            for src in sources:
                is_due = False
                if src.last_success_at is None:
                    is_due = True
                else:
                    elapsed_minutes = (now - src.last_success_at).total_seconds() / 60
                    if elapsed_minutes >= src.refresh_interval_minutes:
                        is_due = True

                if is_due:
                    logger.info("Dispatching ingestion for due source", slug=src.slug, source_id=str(src.id))
                    run_source.delay(str(src.id), triggered_by="scheduler")
                    dispatched.append(src.slug)

        return dispatched

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        dispatched_slugs = loop.run_until_complete(_find_and_dispatch())
        return {"dispatched_count": len(dispatched_slugs), "sources": dispatched_slugs}
    finally:
        loop.close()
