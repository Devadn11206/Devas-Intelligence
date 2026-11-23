import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.db.models.intel import EventCluster, Document
from app.core.embeddings import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventClusterer:
    """Clusters incoming documents into semantic EventClusters using pgvector cosine similarity."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None, threshold: float = 0.86):
        self.embedding_service = embedding_service or get_embedding_service()
        self.threshold = threshold

    async def assign_cluster(self, db: AsyncSession, doc: Document) -> EventCluster:
        """Finds or creates an EventCluster for the given Document."""
        # 1. Compute document-level embedding from Title + Summary
        cluster_text = f"{doc.title}. {doc.summary_raw}"
        doc_vector = self.embedding_service.embed_query(cluster_text)

        # 2. Query existing clusters updated within the last 7 days
        cutoff = utc_now() - timedelta(days=7)
        # Cosine distance in pgvector: distance = 1 - similarity.
        # similarity >= 0.86 means distance <= (1 - 0.86) = 0.14
        max_distance = round(1.0 - self.threshold, 4)

        # Order by cosine distance: EventCluster.centroid_embedding.cosine_distance(doc_vector)
        stmt = (
            select(
                EventCluster,
                EventCluster.centroid_embedding.cosine_distance(doc_vector).label("distance"),
            )
            .where(
                and_(
                    EventCluster.centroid_embedding.is_not(None),
                    EventCluster.last_updated_at >= cutoff,
                )
            )
            .order_by("distance")
            .limit(1)
        )

        res = await db.execute(stmt)
        match = res.first()

        if match and match.distance is not None and match.distance <= max_distance:
            cluster, dist = match
            logger.info(
                "Document %s matched existing cluster %s (dist=%.4f, sim=%.4f)",
                doc.title[:30],
                cluster.canonical_title[:30],
                dist,
                1 - dist,
            )
            # Update centroid embedding (weighted average or incremental update)
            old_count = cluster.document_count
            new_count = old_count + 1
            old_centroid = cluster.centroid_embedding or doc_vector
            new_centroid = [
                round(((old_centroid[i] * old_count) + doc_vector[i]) / new_count, 6)
                for i in range(len(doc_vector))
            ]

            cluster.centroid_embedding = new_centroid
            cluster.document_count = new_count
            cluster.last_updated_at = utc_now()
            doc.event_cluster_id = cluster.id

            await db.commit()
            await db.refresh(cluster)
            return cluster

        # 3. No close match: Create a new EventCluster
        logger.info("Creating new cluster for document: %s", doc.title[:30])
        new_cluster = EventCluster(
            canonical_title=doc.title,
            summary=doc.summary_raw[:500] if doc.summary_raw else doc.title,
            primary_document_id=doc.id,
            centroid_embedding=doc_vector,
            document_count=1,
            first_seen_at=doc.published_at or utc_now(),
            last_updated_at=utc_now(),
        )
        db.add(new_cluster)
        await db.commit()
        await db.refresh(new_cluster)

        doc.event_cluster_id = new_cluster.id
        await db.commit()
        return new_cluster
