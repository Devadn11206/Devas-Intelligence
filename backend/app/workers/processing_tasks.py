import asyncio
import uuid
import structlog
from app.workers.celery_app import celery_app
from app.db.session import async_session_factory
from app.modules.processing.service import ProcessingService

logger = structlog.get_logger(__name__)


@celery_app.task(name="processing.process_document", queue="processing", acks_late=True)
def process_document(document_id: str) -> dict:
    """Celery worker task to process a single document."""
    logger.info("Starting processing.process_document task", document_id=document_id)

    async def _execute() -> dict:
        async with async_session_factory() as session:
            service = ProcessingService()
            doc = await service.process_document(session, uuid.UUID(document_id))
            return {
                "document_id": str(doc.id),
                "status": doc.processing_status.value,
                "cluster_id": str(doc.event_cluster_id) if doc.event_cluster_id else None,
                "error": doc.processing_error,
            }

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_execute())
    finally:
        loop.close()


@celery_app.task(name="processing.process_pending_batch", queue="processing", acks_late=True)
def process_pending_batch(limit: int = 50) -> dict:
    """Processes unindexed raw_ingested documents in batch."""
    logger.info("Executing processing.process_pending_batch task", limit=limit)

    async def _execute() -> dict:
        async with async_session_factory() as session:
            service = ProcessingService()
            docs = await service.process_pending_batch(session, limit=limit)
            return {
                "count": len(docs),
                "processed_ids": [str(d.id) for d in docs],
            }

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_execute())
    finally:
        loop.close()
