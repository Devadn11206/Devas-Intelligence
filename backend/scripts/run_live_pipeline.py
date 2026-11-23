import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Register all adapters
import app.modules.ingestion.adapters

from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models.intel import Source, Document, ProcessingStatus
from app.modules.ingestion.service import IngestionService
from app.modules.processing.service import ProcessingService
from app.modules.linking.linker import EntityLinkerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_pipeline")


async def run_live_pipeline():
    logger.info("Starting live production ingestion, processing, and entity linking...")
    
    # 1. Fetch enabled sources as pure tuples
    async with async_session_factory() as session:
        res = await session.execute(
            select(Source.id, Source.slug, Source.name, Source.adapter_key).where(Source.is_enabled == True)
        )
        sources_info = res.all()
        logger.info("Found %d active production sources.", len(sources_info))

    # 2. Ingest from each source in separate session transactions
    total_ingested = 0
    for s_id, s_slug, s_name, adapter_key in sources_info:
        logger.info("--> Ingesting from Source: '%s' (%s, adapter: %s)", s_name, s_slug, adapter_key)
        try:
            async with async_session_factory() as session:
                job = await IngestionService.run_source_ingestion(
                    db=session,
                    source_id=s_id,
                    triggered_by="manual_live_run"
                )
                logger.info(
                    "    Completed ingestion job %s: status=%s, fetched=%d, inserted=%d, quarantined=%d",
                    job.id, job.status.value, job.records_fetched, job.records_inserted, job.records_quarantined
                )
                total_ingested += job.records_inserted
        except Exception as e:
            logger.error("    Failed ingestion for %s: %s", s_slug, e)

    # 3. Process all pending raw_ingested documents
    async with async_session_factory() as session:
        unprocessed_res = await session.execute(
            select(Document.id).where(Document.processing_status == ProcessingStatus.RAW_INGESTED)
        )
        doc_ids = unprocessed_res.scalars().all()
    
    logger.info("--> Processing %d newly ingested documents (chunking, embeddings, structured LLM extraction, clustering)...", len(doc_ids))
    processing_service = ProcessingService()
    processed_count = 0
    for doc_id in doc_ids:
        try:
            async with async_session_factory() as session:
                await processing_service.process_document(db=session, document_id=doc_id)
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == len(doc_ids):
                logger.info("    Processed %d/%d documents...", processed_count, len(doc_ids))
        except Exception as e:
            logger.error("    Error processing document %s: %s", doc_id, e)

    # 4. Global Entity Linking across all processed documents
    logger.info("--> Running global entity linking pass...")
    async with async_session_factory() as session:
        all_docs_res = await session.execute(select(Document.id))
        all_ids = all_docs_res.scalars().all()

    linked_edges_total = 0
    for d_id in all_ids:
        try:
            async with async_session_factory() as session:
                linker = EntityLinkerService(db=session)
                links = await linker.link_document(d_id)
                linked_edges_total += len(links)
        except Exception as e:
            logger.debug("Linking error on doc %s: %s", d_id, e)

    logger.info(
        "=== Live Production Pipeline Complete! Total Ingested: %d, Processed: %d, Total Entity Edges: %d ===",
        total_ingested, processed_count, linked_edges_total
    )


if __name__ == "__main__":
    asyncio.run(run_live_pipeline())
