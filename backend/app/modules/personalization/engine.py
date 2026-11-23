"""Personalization Engine & Semantic Watchlist Matching.

Implements Module 7:
- User interest profile vector matching: score = 0.5 * topic_overlap + 0.5 * cosine_sim(bookmark_centroid, doc_embedding).
- Semantic Watchlist background matcher: Evaluates incoming documents against active watchlists.
  Generates in-app tenant.notifications when cosine similarity exceeds min_similarity (default 0.78).
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.tenant import User, UserPreference, Bookmark, SemanticWatchlist, Notification
from app.db.models.intel import Document, DocumentChunk

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class PersonalizationEngine:
    """Computes personalized recommendation scores and executes semantic watchlist alerts."""

    @staticmethod
    async def match_document_to_watchlists(
        document: Document,
        doc_embedding: List[float],
        db: AsyncSession,
    ) -> List[Notification]:
        """Matches a document against all active watchlists across tenants and creates notifications."""
        if not doc_embedding:
            return []

        # Find all active watchlists
        stmt = select(SemanticWatchlist).where(SemanticWatchlist.is_active == True)
        res = await db.execute(stmt)
        active_watchlists = res.scalars().all()

        created_notifications: List[Notification] = []

        for watchlist in active_watchlists:
            if not watchlist.query_embedding:
                continue

            sim = cosine_similarity(watchlist.query_embedding, doc_embedding)
            if sim >= watchlist.min_similarity:
                # Check if notification already delivered for this user & doc
                existing_check = await db.execute(
                    select(Notification).where(
                        Notification.user_id == watchlist.user_id,
                        Notification.document_id == document.id,
                    )
                )
                if existing_check.scalar_one_or_none():
                    continue

                pct_match = int(round(sim * 100))
                notif = Notification(
                    id=uuid.uuid4(),
                    user_id=watchlist.user_id,
                    watchlist_id=watchlist.id,
                    document_id=document.id,
                    title=f"Watchlist Alert: {watchlist.name} ({pct_match}% match)",
                    message=f"New intelligence '{document.title}' matches your semantic query '{watchlist.query_text}'.",
                    is_read=False,
                )
                db.add(notif)
                created_notifications.append(notif)

        if created_notifications:
            await db.flush()

        return created_notifications

    @staticmethod
    async def calculate_for_you_score(
        user: User,
        document: Document,
        doc_embedding: Optional[List[float]],
        db: AsyncSession,
    ) -> float:
        """Computes dynamic personalized relevance score for a user (0.0 to 1.0)."""
        score = 0.0

        # 1. Topic overlap score (0.0 to 0.5)
        user_topics = []
        if user.preferences and user.preferences.followed_topics:
            user_topics = [t.lower() for t in user.preferences.followed_topics]

        doc_tags = [t.lower() for t in (document.tags or [])]
        overlap_count = sum(1 for t in user_topics if any(t in dt or dt in t for dt in doc_tags))

        if user_topics:
            topic_score = min(0.5, (overlap_count / len(user_topics)) * 0.5)
        else:
            topic_score = 0.25  # Neutral default

        score += topic_score

        # 2. Bookmark Vector Similarity (0.0 to 0.5)
        if doc_embedding:
            # Query recent bookmarked documents for user
            b_stmt = select(Bookmark.entity_id).where(Bookmark.user_id == user.id).limit(10)
            b_res = await db.execute(b_stmt)
            bookmarked_ids = b_res.scalars().all()

            if bookmarked_ids:
                # Query embeddings of chunks of these bookmarked docs
                chunk_stmt = select(DocumentChunk.embedding).where(
                    DocumentChunk.document_id.in_(bookmarked_ids),
                    DocumentChunk.embedding.is_not(None),
                ).limit(20)
                c_res = await db.execute(chunk_stmt)
                embeddings = [row[0] for row in c_res.all() if row[0] is not None]

                if embeddings:
                    # Average similarity to bookmarks
                    sims = [cosine_similarity(doc_embedding, emb) for emb in embeddings]
                    avg_sim = max(0.0, float(np.mean(sims)))
                    score += min(0.5, avg_sim * 0.5)
                else:
                    score += 0.25
            else:
                score += 0.25
        else:
            score += 0.25

        return round(min(1.0, max(0.0, score)), 4)
