import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.intel import Document, DocumentChunk, ProcessingStatus
from app.modules.processing.chunker import chunk_document
from app.modules.processing.extractor import StructuredExtractor
from app.modules.processing.clusterer import EventClusterer
from app.core.embeddings import EmbeddingService, get_embedding_service
from app.core.llm_provider import BaseLLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessingService:
    """Orchestrates chunking, vector embedding, structured extraction, and event clustering."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.extractor = StructuredExtractor(provider=llm_provider or get_llm_provider())
        self.clusterer = EventClusterer(embedding_service=self.embedding_service)

    async def process_document(self, db: AsyncSession, document_id: uuid.UUID) -> Document:
        """Processes a single raw_ingested Document."""
        res = await db.execute(select(Document).where(Document.id == document_id))
        doc = res.scalars().first()
        if not doc:
            raise ValueError(f"Document with id {document_id} not found")

        try:
            # 1. Section-aware text chunking
            raw_chunks = chunk_document(
                title=doc.title,
                summary_raw=doc.summary_raw,
                content_raw=doc.content_raw,
                content_type=doc.content_type.value,
            )

            # 2. Generate embeddings for each chunk
            chunk_texts = [c.content for c in raw_chunks]
            chunk_vectors = self.embedding_service.embed_documents(chunk_texts)

            # Clean up any existing chunks for idempotency / re-runs
            await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

            for chunk_data, vec in zip(raw_chunks, chunk_vectors):
                chunk_rec = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk_data.chunk_index,
                    section_type=chunk_data.section_type,
                    content=chunk_data.content,
                    token_count=chunk_data.token_count,
                    embedding=vec,
                )
                db.add(chunk_rec)

            # 3. Structured LLM Technical Extraction (Fact vs AI Separation: populates summary_ai only)
            summary_ai_dict, extracted_tags = await self.extractor.extract_structured_analysis(doc)
            doc.summary_ai = summary_ai_dict

            # Merge any new tags into doc.tags without duplicates
            current_tags = set(doc.tags or [])
            for t in extracted_tags:
                if t and isinstance(t, str):
                    current_tags.add(t.strip().lower())
            doc.tags = sorted(list(current_tags))

            # 4. Semantic Event Clustering
            await self.clusterer.assign_cluster(db=db, doc=doc)

            # 5. Mark document processed
            doc.processing_status = ProcessingStatus.PROCESSED
            doc.processed_at = utc_now()
            doc.processing_error = None

            await db.commit()
            await db.refresh(doc)

            # 6. Immediate Entity Linking Hook
            try:
                from app.modules.linking.linker import EntityLinkerService
                await EntityLinkerService(db=db).link_document(doc.id)
            except Exception as link_err:
                logger.warning("Entity linking non-fatal error for doc %s: %s", doc.id, link_err)

            logger.info("Successfully processed document id=%s, title='%s'", doc.id, doc.title[:30])
            return doc

        except Exception as exc:
            logger.error("Failed to process document id=%s: %s", doc.id, exc, exc_info=True)
            await db.rollback()

            # Record failure state on document
            doc.processing_status = ProcessingStatus.FAILED
            doc.processing_error = str(exc)
            doc.processed_at = utc_now()
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            return doc

    async def process_pending_batch(self, db: AsyncSession, limit: int = 50) -> List[Document]:
        """Processes up to `limit` raw_ingested documents."""
        res = await db.execute(
            select(Document)
            .where(Document.processing_status == ProcessingStatus.RAW_INGESTED)
            .order_by(Document.ingested_at.asc())
            .limit(limit)
        )
        docs = res.scalars().all()
        processed_docs = []
        for d in docs:
            processed = await self.process_document(db, d.id)
            processed_docs.append(processed)
        return processed_docs
