import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.tenant import User, UserPreference, Bookmark, DigestFrequency, SemanticWatchlist, Notification
from app.api.deps import get_current_user
from app.core.embeddings import get_embedding_service
from app.schemas.tenant import (
    UserPreferencesResponse,
    UserPreferencesUpdate,
    BookmarkCreate,
    BookmarkResponse,
    WatchlistCreateRequest,
    WatchlistResponse,
    NotificationResponse,
)

router = APIRouter(prefix="/users", tags=["Users & Tenant Preferences"])


# ---------------- USER PREFERENCES (RLS Protected) ----------------
@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    res = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    pref = res.scalar_one_or_none()

    if not pref:
        # Create default preference if none exists
        pref = UserPreference(
            user_id=current_user.id,
            followed_topics=["AI Agents", "LLM Inference"],
            followed_technologies=["vLLM", "PyTorch"],
            followed_repos=["vllm-project/vllm"],
            digest_frequency=DigestFrequency.WEEKLY,
        )
        db.add(pref)
        await db.flush()

    return UserPreferencesResponse(
        id=pref.id,
        user_id=pref.user_id,
        followed_topics=pref.followed_topics,
        followed_technologies=pref.followed_technologies,
        followed_repos=pref.followed_repos,
        digest_frequency=pref.digest_frequency,
        updated_at=pref.updated_at,
    )


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_my_preferences(
    req: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferencesResponse:
    res = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    pref = res.scalar_one_or_none()

    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)

    if req.followed_topics is not None:
        pref.followed_topics = req.followed_topics
    if req.followed_technologies is not None:
        pref.followed_technologies = req.followed_technologies
    if req.followed_repos is not None:
        pref.followed_repos = req.followed_repos
    if req.digest_frequency is not None:
        pref.digest_frequency = req.digest_frequency

    await db.flush()
    return UserPreferencesResponse(
        id=pref.id,
        user_id=pref.user_id,
        followed_topics=pref.followed_topics,
        followed_technologies=pref.followed_technologies,
        followed_repos=pref.followed_repos,
        digest_frequency=pref.digest_frequency,
        updated_at=pref.updated_at,
    )


# ---------------- BOOKMARKS (RLS Protected) ----------------
@router.get("/me/bookmarks", response_model=List[BookmarkResponse])
async def get_my_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[BookmarkResponse]:
    res = await db.execute(
        select(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
    )
    bookmarks = res.scalars().all()
    return [
        BookmarkResponse(
            id=b.id,
            user_id=b.user_id,
            entity_type=b.entity_type,
            entity_id=b.entity_id,
            notes=b.notes,
            created_at=b.created_at,
        )
        for b in bookmarks
    ]


@router.post("/me/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    req: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookmarkResponse:
    # Check duplicate
    existing = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id,
            Bookmark.entity_type == req.entity_type,
            Bookmark.entity_id == req.entity_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is already bookmarked by user",
        )

    bookmark = Bookmark(
        user_id=current_user.id,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        notes=req.notes,
    )
    db.add(bookmark)
    await db.flush()

    return BookmarkResponse(
        id=bookmark.id,
        user_id=bookmark.user_id,
        entity_type=bookmark.entity_type,
        entity_id=bookmark.entity_id,
        notes=bookmark.notes,
        created_at=bookmark.created_at,
    )


@router.delete("/me/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == current_user.id)
    )
    bookmark = res.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    await db.delete(bookmark)


# ---------------- SEMANTIC WATCHLISTS (RLS Protected — Phase 7) ----------------
@router.get("/me/watchlists", response_model=List[WatchlistResponse])
async def list_my_watchlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WatchlistResponse]:
    """Retrieves user's semantic watchlists (filtered by current user RLS)."""
    res = await db.execute(
        select(SemanticWatchlist)
        .where(SemanticWatchlist.user_id == current_user.id)
        .order_by(SemanticWatchlist.created_at.desc())
    )
    watchlists = res.scalars().all()
    return [
        WatchlistResponse(
            id=w.id,
            user_id=w.user_id,
            name=w.name,
            query_text=w.query_text,
            min_similarity=w.min_similarity,
            is_active=w.is_active,
            created_at=w.created_at,
        )
        for w in watchlists
    ]


@router.post("/me/watchlists", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_my_watchlist(
    req: WatchlistCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistResponse:
    """Creates a semantic watchlist with 768-dim query embedding and executes an instant live match scan against recent documents."""
    from app.db.models.intel import Document, DocumentChunk

    embedding_svc = get_embedding_service()
    embedding = embedding_svc.embed_query(req.query_text)

    watchlist = SemanticWatchlist(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=req.name,
        query_text=req.query_text,
        query_embedding=embedding,
        min_similarity=req.min_similarity,
        is_active=req.is_active,
    )
    db.add(watchlist)
    await db.flush()

    # Instant live match scan against indexed document chunks
    initial_matches_count = 0
    try:
        sim_expr = (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("similarity")
        match_stmt = (
            select(DocumentChunk, Document, sim_expr)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(sim_expr >= req.min_similarity)
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(5)
        )
        match_res = await db.execute(match_stmt)
        matched_rows = match_res.all()

        seen_doc_ids = set()
        for chunk_obj, doc_obj, sim_val in matched_rows:
            if doc_obj.id not in seen_doc_ids:
                seen_doc_ids.add(doc_obj.id)
                # Create real notification
                notif = Notification(
                    id=uuid.uuid4(),
                    user_id=current_user.id,
                    watchlist_id=watchlist.id,
                    document_id=doc_obj.id,
                    title=f"Watchlist Hit: {watchlist.name}",
                    message=f"Matched '{doc_obj.title[:80]}' with {sim_val * 100:.1f}% semantic similarity.",
                    is_read=False,
                )
                db.add(notif)
                initial_matches_count += 1
        await db.flush()
    except Exception as e:
        logger = logging.getLogger("app.api.users")
        logger.warning(f"Initial watchlist match scan skipped or failed: {e}")

    return WatchlistResponse(
        id=watchlist.id,
        user_id=watchlist.user_id,
        name=watchlist.name,
        query_text=watchlist.query_text,
        min_similarity=watchlist.min_similarity,
        is_active=watchlist.is_active,
        created_at=watchlist.created_at,
        initial_matches_count=initial_matches_count,
    )


@router.delete("/me/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_watchlist(
    watchlist_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(
        select(SemanticWatchlist).where(
            SemanticWatchlist.id == watchlist_id,
            SemanticWatchlist.user_id == current_user.id,
        )
    )
    watchlist = res.scalar_one_or_none()
    if not watchlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")

    await db.delete(watchlist)


# ---------------- NOTIFICATIONS (RLS Protected — Phase 7) ----------------
@router.get("/me/notifications", response_model=List[NotificationResponse])
async def list_my_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[NotificationResponse]:
    """Retrieves notifications generated by semantic watchlists and system alerts."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)

    res = await db.execute(stmt)
    notifications = res.scalars().all()
    return [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            watchlist_id=n.watchlist_id,
            document_id=n.document_id,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.patch("/me/notifications/read-all", response_model=List[NotificationResponse])
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[NotificationResponse]:
    """Marks all unread notifications as read for current user."""
    res = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    unread_notifs = res.scalars().all()
    for n in unread_notifs:
        n.is_read = True
    await db.flush()

    # Return updated list
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
    )
    all_res = await db.execute(stmt)
    notifications = all_res.scalars().all()
    return [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            watchlist_id=n.watchlist_id,
            document_id=n.document_id,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.patch("/me/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    res = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = res.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    await db.flush()

    return NotificationResponse(
        id=notif.id,
        user_id=notif.user_id,
        watchlist_id=notif.watchlist_id,
        document_id=notif.document_id,
        title=notif.title,
        message=notif.message,
        is_read=notif.is_read,
        created_at=notif.created_at,
    )

