import enum
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Computed,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, TSVECTOR
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import IntelBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceCategory(str, enum.Enum):
    RESEARCH = "research"
    ACADEMIC_METADATA = "academic_metadata"
    CODE = "code"
    MODEL_ECOSYSTEM = "model_ecosystem"
    COMPANY_BLOG = "company_blog"
    TECH_NEWS = "tech_news"


class SourceHealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"


class IngestionJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class ContentType(str, enum.Enum):
    PAPER = "paper"
    REPO = "repo"
    MODEL = "model"
    ARTICLE = "article"
    TOOL = "tool"


class ProcessingStatus(str, enum.Enum):
    RAW_INGESTED = "raw_ingested"
    PROCESSED = "processed"
    FAILED = "failed"


class RelationType(str, enum.Enum):
    IMPLEMENTS = "IMPLEMENTS"
    CITES = "CITES"
    USES_MODEL = "USES_MODEL"
    USES_DATASET = "USES_DATASET"
    RELEASED_BY = "RELEASED_BY"
    RELATED_TO = "RELATED_TO"


class LinkMethod(str, enum.Enum):
    DETERMINISTIC_URL = "deterministic_url"
    ARXIV_ID_MATCH = "arxiv_id_match"
    SEMANTIC_AUTHOR_MATCH = "semantic_author_match"


class SignalClassification(str, enum.Enum):
    BREAKTHROUGH_MOMENTUM = "breakthrough_momentum"
    HYPE_SPIKE = "hype_spike"
    STEADY_ADOPTION = "steady_adoption"
    COOLING = "cooling"


class ConsensusStatus(str, enum.Enum):
    VERIFIED_CONSENSUS = "verified_consensus"
    SINGLE_SOURCE = "single_source"
    DISPUTED = "disputed"


class Source(IntelBase):
    """Source Registry table (`intel.sources` — ING-001 to ING-018)."""
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[SourceCategory] = mapped_column(
        SAEnum(SourceCategory, name="source_category", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    adapter_key: Mapped[str] = mapped_column(String(50), nullable=False)  # arxiv, github, huggingface, semantic_scholar, rss
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    refresh_interval_minutes: Mapped[int] = mapped_column(Integer, default=360, nullable=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    health_status: Mapped[SourceHealthStatus] = mapped_column(
        SAEnum(SourceHealthStatus, name="source_health_status", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        default=SourceHealthStatus.HEALTHY,
        nullable=False,
    )
    attribution_text: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    license_terms: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    jobs: Mapped[List["IngestionJob"]] = relationship(
        "IngestionJob", back_populates="source", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="source", cascade="all, delete-orphan"
    )
    quarantined_records: Mapped[List["QuarantinedRecord"]] = relationship(
        "QuarantinedRecord", back_populates="source", cascade="all, delete-orphan"
    )


class IngestionJob(IntelBase):
    """Execution Audit Trail table (`intel.ingestion_jobs` — ARC-008, ING-005)."""
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[IngestionJobStatus] = mapped_column(
        SAEnum(IngestionJobStatus, name="ingestion_job_status", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        default=IngestionJobStatus.QUEUED,
        nullable=False,
    )
    triggered_by: Mapped[str] = mapped_column(String(50), default="scheduler", nullable=False)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_quarantined: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped["Source"] = relationship("Source", back_populates="jobs")
    quarantined_records: Mapped[List["QuarantinedRecord"]] = relationship(
        "QuarantinedRecord", back_populates="job", cascade="all, delete-orphan"
    )


class QuarantinedRecord(IntelBase):
    """Dead-Letter Store table (`intel.quarantined_records` — ING-008)."""
    __tablename__ = "quarantined_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.ingestion_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    validation_error: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    source: Mapped["Source"] = relationship("Source", back_populates="quarantined_records")
    job: Mapped["IngestionJob"] = relationship("IngestionJob", back_populates="quarantined_records")


class EventCluster(IntelBase):
    """Canonical Event Grouping (`intel.event_clusters` — Phase 3 Deduplication vs Clustering)."""
    __tablename__ = "event_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.documents.id", ondelete="SET NULL"), nullable=True
    )
    centroid_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    consensus_status: Mapped[ConsensusStatus] = mapped_column(
        SAEnum(ConsensusStatus, name="consensus_status", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        default=ConsensusStatus.SINGLE_SOURCE,
        nullable=False,
    )
    consensus_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="event_cluster",
        foreign_keys="Document.event_cluster_id",
    )


class Document(IntelBase):
    """Canonical Normalized Content table (`intel.documents` — ING-007, ING-010, ING-015, Phase 3)."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.event_clusters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content_type: Mapped[ContentType] = mapped_column(
        SAEnum(ContentType, name="content_type", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary_raw: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary_ai: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    content_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(ProcessingStatus, name="processing_status", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        default=ProcessingStatus.RAW_INGESTED,
        nullable=False,
        index=True,
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    source: Mapped["Source"] = relationship("Source", back_populates="documents")
    event_cluster: Mapped[Optional["EventCluster"]] = relationship(
        "EventCluster",
        back_populates="documents",
        foreign_keys=[event_cluster_id],
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    outgoing_links: Mapped[List["EntityLink"]] = relationship(
        "EntityLink",
        back_populates="source_entity",
        foreign_keys="EntityLink.source_entity_id",
        cascade="all, delete-orphan",
    )
    incoming_links: Mapped[List["EntityLink"]] = relationship(
        "EntityLink",
        back_populates="target_entity",
        foreign_keys="EntityLink.target_entity_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),
        Index("ix_documents_type_published", "content_type", "published_at"),
    )


class DocumentChunk(IntelBase):
    """Hybrid Lexical + Dense Vector Store (`intel.document_chunks` — Phase 3)."""
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), default="overview", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(content, ''))", persisted=True),
        nullable=True,
    )
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class EntityLink(IntelBase):
    """Relational Knowledge Graph (`intel.entity_links` — Phase 4 Module 8)."""
    __tablename__ = "entity_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intel.documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[RelationType] = mapped_column(
        SAEnum(RelationType, name="relation_type", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    link_method: Mapped[LinkMethod] = mapped_column(
        SAEnum(LinkMethod, name="link_method", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    evidence_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    source_entity: Mapped["Document"] = relationship(
        "Document", foreign_keys=[source_entity_id], back_populates="outgoing_links"
    )
    target_entity: Mapped["Document"] = relationship(
        "Document", foreign_keys=[target_entity_id], back_populates="incoming_links"
    )

    __table_args__ = (
        CheckConstraint("source_entity_id != target_entity_id", name="ck_no_self_loops"),
        UniqueConstraint("source_entity_id", "target_entity_id", "relation_type", name="uq_source_target_relation"),
    )


class TrendSnapshot(IntelBase):
    """Time-Series Velocity & Hype-vs-Substance Metrics (`intel.trend_snapshots` — Phase 7 Module 7)."""
    __tablename__ = "trend_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(100), default="AI & Software", nullable=False, index=True)
    window_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    paper_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repo_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    news_count_7d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    velocity_growth_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hype_to_substance_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    signal_classification: Mapped[SignalClassification] = mapped_column(
        SAEnum(SignalClassification, name="signal_classification", schema="intel", values_callable=lambda obj: [e.value for e in obj]),
        default=SignalClassification.STEADY_ADOPTION,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("topic_tag", "window_date", name="uq_trend_topic_window_date"),
        Index("ix_trend_snapshots_topic_date", "topic_tag", "window_date"),
    )


class AgentRun(IntelBase):
    """Telemetry records for Autonomous Multi-Agent Workflows (`intel.agent_runs` — Phase 5 & 8)."""
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    query_or_topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False, index=True)
    steps_executed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    step_details: Mapped[List[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

