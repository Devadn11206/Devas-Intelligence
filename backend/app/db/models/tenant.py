import enum
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import TenantBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    GUEST = "guest"
    USER = "user"
    ORG_MEMBER = "org_member"
    ORG_ADMIN = "org_admin"
    PLATFORM_MODERATOR = "platform_moderator"
    PLATFORM_ADMIN = "platform_admin"
    SUPER_ADMIN = "super_admin"


class OrgMemberRole(str, enum.Enum):
    ORG_MEMBER = "org_member"
    ORG_ADMIN = "org_admin"


class BookmarkEntityType(str, enum.Enum):
    PAPER = "paper"
    REPO = "repo"
    MODEL = "model"
    ARTICLE = "article"
    TOOL = "tool"


class DigestFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    OFF = "off"


class BriefingType(str, enum.Enum):
    DAILY_DIGEST = "daily_digest"
    DEEP_DOSSIER = "deep_dossier"
    WEEKLY_RADAR = "weekly_radar"


class User(TenantBase):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", schema="tenant", values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    oauth_sub: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    preferences: Mapped[Optional["UserPreference"]] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    bookmarks: Mapped[List["Bookmark"]] = relationship(
        "Bookmark", back_populates="user", cascade="all, delete-orphan"
    )
    watchlists: Mapped[List["SemanticWatchlist"]] = relationship(
        "SemanticWatchlist", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    briefings: Mapped[List["UserBriefing"]] = relationship(
        "UserBriefing", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    org_memberships: Mapped[List["OrganizationMember"]] = relationship(
        "OrganizationMember", back_populates="user", cascade="all, delete-orphan"
    )


class Organization(TenantBase):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    members: Mapped[List["OrganizationMember"]] = relationship(
        "OrganizationMember", back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(TenantBase):
    __tablename__ = "organization_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[OrgMemberRole] = mapped_column(
        SAEnum(OrgMemberRole, name="org_member_role", schema="tenant", values_callable=lambda obj: [e.value for e in obj]),
        default=OrgMemberRole.ORG_MEMBER,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="org_memberships")

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )


class RefreshToken(TenantBase):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class UserPreference(TenantBase):
    """Private entity protected by PostgreSQL Row-Level Security (RLS)."""
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    followed_topics: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    followed_technologies: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    followed_repos: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    digest_frequency: Mapped[DigestFrequency] = mapped_column(
        SAEnum(DigestFrequency, name="digest_frequency", schema="tenant", values_callable=lambda obj: [e.value for e in obj]),
        default=DigestFrequency.WEEKLY,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="preferences")


class Bookmark(TenantBase):
    """Private entity protected by PostgreSQL Row-Level Security (RLS)."""
    __tablename__ = "bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    entity_type: Mapped[BookmarkEntityType] = mapped_column(
        SAEnum(BookmarkEntityType, name="bookmark_entity_type", schema="tenant", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="bookmarks")

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_user_entity_bookmark"),
        Index("ix_bookmarks_user_entity", "user_id", "entity_type"),
    )


class SemanticWatchlist(TenantBase):
    """Private entity protected by PostgreSQL Row-Level Security (RLS — SEC-005)."""
    __tablename__ = "semantic_watchlists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)
    min_similarity: Mapped[float] = mapped_column(Float, default=0.78, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="watchlists")
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="watchlist", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_watchlists_embedding_hnsw",
            "query_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"query_embedding": "vector_cosine_ops"},
        ),
    )


class Notification(TenantBase):
    """Private entity protected by PostgreSQL Row-Level Security (RLS — SEC-005)."""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    watchlist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.semantic_watchlists.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")
    watchlist: Mapped[Optional["SemanticWatchlist"]] = relationship("SemanticWatchlist", back_populates="notifications")


class AuditLog(TenantBase):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class UserBriefing(TenantBase):
    """Private entity protected by PostgreSQL Row-Level Security (RLS — SEC-005)."""
    __tablename__ = "user_briefings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    briefing_type: Mapped[BriefingType] = mapped_column(
        SAEnum(BriefingType, name="briefing_type", schema="tenant", values_callable=lambda obj: [e.value for e in obj]),
        default=BriefingType.DEEP_DOSSIER,
        nullable=False,
        index=True,
    )
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source_count: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="briefings")

