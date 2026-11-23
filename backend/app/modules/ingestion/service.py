import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
import httpx
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.intel import (
    Source,
    SourceCategory,
    SourceHealthStatus,
    IngestionJob,
    IngestionJobStatus,
    QuarantinedRecord,
    Document,
    ProcessingStatus,
)
from app.modules.ingestion.base import AdapterRegistry, CanonicalRecord

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DEFAULT_SOURCES = [
    {
        "name": "arXiv Scientific ML & PINNs",
        "slug": "arxiv-sciml",
        "category": SourceCategory.RESEARCH,
        "adapter_key": "arxiv",
        "base_url": "https://export.arxiv.org/api/query",
        "config": {
            "query": "cat:cs.LG OR cat:cs.AI OR cat:math.NA",
            "max_results": 25,
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "arXiv.org e-Print archive",
        "license_terms": "arXiv non-exclusive license / CC-BY",
    },
    {
        "name": "arXiv AI & LLM Systems",
        "slug": "arxiv-ai-systems",
        "category": SourceCategory.RESEARCH,
        "adapter_key": "arxiv",
        "base_url": "https://export.arxiv.org/api/query",
        "config": {
            "query": "cat:cs.DC OR cat:cs.SE",
            "max_results": 25,
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "arXiv.org e-Print archive",
        "license_terms": "arXiv non-exclusive license / CC-BY",
    },
    {
        "name": "GitHub AI & SciML Repos",
        "slug": "github-sciml",
        "category": SourceCategory.CODE,
        "adapter_key": "github",
        "base_url": "https://api.github.com",
        "config": {
            "query": "topic:scientific-machine-learning OR topic:physics-informed-neural-networks",
            "sort": "stars",
            "order": "desc",
            "max_results": 20,
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "GitHub REST API",
        "license_terms": "Open Source Licenses per repository",
    },
    {
        "name": "Hugging Face Trending Models",
        "slug": "hf-trending-models",
        "category": SourceCategory.MODEL_ECOSYSTEM,
        "adapter_key": "huggingface",
        "base_url": "https://huggingface.co/api",
        "config": {
            "sort": "trendingScore",
            "direction": -1,
            "limit": 25,
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "Hugging Face Hub",
        "license_terms": "Model-specific open weights licenses",
    },
    {
        "name": "Semantic Scholar SciML",
        "slug": "semantic-scholar-sciml",
        "category": SourceCategory.ACADEMIC_METADATA,
        "adapter_key": "semantic_scholar",
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "config": {
            "query": "scientific machine learning PINNs",
            "limit": 25,
        },
        "refresh_interval_minutes": 720,
        "rate_limit_rpm": 15,
        "attribution_text": "Semantic Scholar Academic Graph",
        "license_terms": "Semantic Scholar API Terms",
    },
    {
        "name": "PyTorch & HF Engineering Blogs",
        "slug": "pytorch-hf-rss",
        "category": SourceCategory.COMPANY_BLOG,
        "adapter_key": "rss",
        "base_url": "https://pytorch.org/feed.xml",
        "config": {
            "feed_url": "https://pytorch.org/feed.xml",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "PyTorch / Hugging Face RSS",
        "license_terms": "Original Author Copyright",
    },
]


async def seed_default_sources(db: AsyncSession) -> List[Source]:
    """Seeds the standard 6 intelligence sources if they do not already exist."""
    created_sources: List[Source] = []
    for src_data in DEFAULT_SOURCES:
        res = await db.execute(select(Source).where(Source.slug == src_data["slug"]))
        existing = res.scalars().first()
        if not existing:
            source = Source(**src_data)
            db.add(source)
            created_sources.append(source)
    await db.commit()
    return created_sources


class IngestionService:
    """Core orchestration service for executing source adapters, validation, and idempotent storage."""

    @staticmethod
    async def run_source_ingestion(
        db: AsyncSession,
        source_id: uuid.UUID,
        triggered_by: str = "scheduler",
        client: Optional[httpx.AsyncClient] = None,
    ) -> IngestionJob:
        """Executes a full ingestion pipeline run for a given source."""
        # 1. Retrieve source
        res = await db.execute(select(Source).where(Source.id == source_id))
        source = res.scalars().first()
        if not source:
            raise ValueError(f"Source with ID '{source_id}' not found.")

        # 2. Create IngestionJob record
        job = IngestionJob(
            source_id=source.id,
            status=IngestionJobStatus.RUNNING,
            triggered_by=triggered_by,
            started_at=utc_now(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        records_fetched = 0
        records_inserted = 0
        records_updated = 0
        records_quarantined = 0

        try:
            # 3. Instantiate adapter
            adapter = AdapterRegistry.get(source.adapter_key, client=client)

            # 4. Fetch raw data
            raw_items = await adapter.fetch(source.config, since=source.last_success_at)
            records_fetched = len(raw_items)

            # 5. Parse
            parsed_items = adapter.parse(raw_items)

            # 6. Normalize
            normalized_items = adapter.normalize(parsed_items, source)

            # 7. Validate
            valid_records, quarantined = adapter.validate(normalized_items)

            # 8. Record quarantined items
            for q_item in quarantined:
                q_record = QuarantinedRecord(
                    source_id=source.id,
                    job_id=job.id,
                    external_id=q_item.get("external_id"),
                    raw_payload=q_item.get("raw_payload", {}),
                    validation_error=q_item.get("validation_error", "Validation error"),
                )
                db.add(q_record)
                records_quarantined += 1

            # 9. Upsert valid canonical records idempotently
            for rec in valid_records:
                hash_val = rec.content_hash
                # Check if document already exists by canonical_url
                doc_query = await db.execute(
                    select(Document).where(Document.canonical_url == rec.canonical_url)
                )
                existing_doc = doc_query.scalars().first()

                if existing_doc is None:
                    # Insert new document
                    new_doc = Document(
                        source_id=source.id,
                        content_type=rec.content_type,
                        external_id=rec.external_id,
                        canonical_url=rec.canonical_url,
                        content_hash=hash_val,
                        title=rec.title,
                        summary_raw=rec.summary_raw,
                        content_raw=rec.content_raw,
                        authors=rec.authors,
                        tags=rec.tags,
                        metadata_=rec.metadata,
                        processing_status=ProcessingStatus.RAW_INGESTED,
                        published_at=rec.published_at,
                        ingested_at=utc_now(),
                    )
                    db.add(new_doc)
                    records_inserted += 1
                else:
                    # Idempotency check: only update if content_hash changed
                    if existing_doc.content_hash != hash_val:
                        existing_doc.content_hash = hash_val
                        existing_doc.title = rec.title
                        existing_doc.summary_raw = rec.summary_raw
                        existing_doc.content_raw = rec.content_raw
                        existing_doc.authors = rec.authors
                        existing_doc.tags = rec.tags
                        existing_doc.metadata_ = rec.metadata
                        existing_doc.processing_status = ProcessingStatus.RAW_INGESTED
                        existing_doc.updated_at = utc_now()
                        records_updated += 1
                    else:
                        # Identical content: no update required
                        pass

            # 10. Update job and source on success
            job.status = IngestionJobStatus.COMPLETED
            job.records_fetched = records_fetched
            job.records_inserted = records_inserted
            job.records_updated = records_updated
            job.records_quarantined = records_quarantined
            job.finished_at = utc_now()

            source.last_success_at = utc_now()
            source.health_status = SourceHealthStatus.HEALTHY
            source.last_error = None

            await db.commit()
            await db.refresh(job)
            return job

        except Exception as exc:
            logger.error("Ingestion failed for source %s: %s", source.slug, exc, exc_info=True)
            await db.rollback()

            # Mark job failed and source failing
            job.status = IngestionJobStatus.FAILED
            job.error_summary = str(exc)
            job.finished_at = utc_now()
            job.records_fetched = records_fetched
            job.records_inserted = records_inserted
            job.records_updated = records_updated
            job.records_quarantined = records_quarantined

            source.health_status = SourceHealthStatus.FAILING
            source.last_failure_at = utc_now()
            source.last_error = str(exc)

            db.add(job)
            db.add(source)
            await db.commit()
            await db.refresh(job)
            return job
