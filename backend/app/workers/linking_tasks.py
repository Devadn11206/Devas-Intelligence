import asyncio
import uuid
import structlog
from app.workers.celery_app import celery_app
from app.db.session import async_session_factory
from app.modules.linking.linker import EntityLinkerService

logger = structlog.get_logger(__name__)


@celery_app.task(name="linking.link_document", queue="processing", acks_late=True)
def link_document(document_id: str) -> dict:
    """Celery task to run 3-pass hybrid entity linking on a document."""
    logger.info("Executing linking.link_document task", document_id=document_id)

    async def _execute() -> dict:
        async with async_session_factory() as session:
            count = await EntityLinkerService.link_document(session, uuid.UUID(document_id))
            return {"document_id": document_id, "links_created": count}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_execute())
    finally:
        loop.close()


@celery_app.task(name="linking.rebuild_graph_batch", queue="processing", acks_late=True)
def rebuild_graph_batch(limit: int = 100) -> dict:
    """Batch reconstructs entity graph edges across processed documents."""
    logger.info("Executing linking.rebuild_graph_batch task", limit=limit)

    async def _execute() -> dict:
        async with async_session_factory() as session:
            count = await EntityLinkerService.rebuild_graph_batch(session, limit=limit)
            return {"rebuilt_links": count}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_execute())
    finally:
        loop.close()
