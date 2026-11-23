import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.intel import (
    SourceCategory,
    SourceHealthStatus,
    IngestionJobStatus,
    ContentType,
    ProcessingStatus,
    RelationType,
    LinkMethod,
    SignalClassification,
    ConsensusStatus,
)


class SourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    category: SourceCategory
    adapter_key: str = Field(..., max_length=50)
    base_url: str = Field(..., max_length=512)
    config: dict[str, Any] = Field(default_factory=dict)
    refresh_interval_minutes: int = Field(default=360, ge=5)
    rate_limit_rpm: int = Field(default=30, ge=1)
    is_enabled: bool = True
    attribution_text: str = Field(default="")
    license_terms: str = Field(default="")


class SourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[SourceCategory] = None
    adapter_key: Optional[str] = None
    base_url: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    refresh_interval_minutes: Optional[int] = None
    rate_limit_rpm: Optional[int] = None
    is_enabled: Optional[bool] = None
    health_status: Optional[SourceHealthStatus] = None
    attribution_text: Optional[str] = None
    license_terms: Optional[str] = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    category: SourceCategory
    adapter_key: str
    base_url: str
    config: dict[str, Any]
    refresh_interval_minutes: int
    rate_limit_rpm: int
    is_enabled: bool
    health_status: SourceHealthStatus
    attribution_text: str
    license_terms: str
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    source_name: Optional[str] = None
    celery_task_id: Optional[str] = None
    status: IngestionJobStatus
    triggered_by: str
    records_fetched: int
    records_inserted: int
    records_updated: int
    records_quarantined: int
    error_summary: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class QuarantinedRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    job_id: uuid.UUID
    external_id: Optional[str] = None
    raw_payload: dict[str, Any]
    validation_error: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    event_cluster_id: Optional[uuid.UUID] = None
    content_type: ContentType
    external_id: str
    canonical_url: str
    content_hash: str
    title: str
    summary_raw: str
    summary_ai: Optional[dict[str, Any]] = None
    content_raw: Optional[str] = None
    authors: List[str]
    tags: List[str]
    metadata: dict[str, Any]
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    published_at: datetime
    processed_at: Optional[datetime] = None
    ingested_at: datetime
    updated_at: datetime


class CorroboratingSource(BaseModel):
    document_id: uuid.UUID
    source_name: str
    canonical_url: str
    published_at: datetime


class IntelFeedCardResponse(BaseModel):
    id: uuid.UUID  # primary document id or cluster id
    event_cluster_id: Optional[uuid.UUID] = None
    primary_document_id: uuid.UUID
    title: str
    content_type: ContentType
    summary_raw: str
    summary_ai: Optional[dict[str, Any]] = None
    authors: List[str]
    tags: List[str]
    metadata: dict[str, Any]
    published_at: datetime
    source_name: str
    source_category: str
    canonical_url: str
    document_count: int = 1
    corroborating_sources: List[CorroboratingSource] = Field(default_factory=list)
    consensus_status: Optional[ConsensusStatus] = None
    consensus_summary: Optional[str] = None
    linked_repos_count: int = 0
    linked_papers_count: int = 0


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    source_name: str
    chunk_count: int
    cluster_document_count: int
    cluster_siblings: List[DocumentResponse] = Field(default_factory=list)


class ProcessingBatchTriggerResponse(BaseModel):
    task_id: Optional[str] = None
    pending_count: int
    enqueued: bool


class ProcessingStatsResponse(BaseModel):
    raw_ingested_count: int
    processed_count: int
    failed_count: int
    total_chunks: int
    total_clusters: int


# ==============================================================================
# Phase 4: Entity Linking & Knowledge Graph Schemas
# ==============================================================================

class EntityLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relation_type: RelationType
    confidence_score: float
    link_method: LinkMethod
    evidence_snippet: str
    direction: str = "outgoing"  # outgoing | incoming relative to queried doc
    linked_document: DocumentResponse
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    title: str
    content_type: ContentType
    canonical_url: str
    source_name: Optional[str] = None
    published_at: Optional[datetime] = None
    is_root: bool = False


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation_type: RelationType
    confidence_score: float
    link_method: LinkMethod
    evidence_snippet: str


class KnowledgeGraphResponse(BaseModel):
    root_document_id: uuid.UUID
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class LinkingBatchTriggerResponse(BaseModel):
    task_id: Optional[str] = None
    enqueued: bool
    batch_size: int


class LinkingStatsResponse(BaseModel):
    total_links: int
    by_relation_type: dict[str, int]
    by_link_method: dict[str, int]


# ==============================================================================
# Phase 7: Trends, Story Evolution & Consensus Schemas
# ==============================================================================

class TrendSnapshotItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic_tag: str
    domain: str
    window_date: datetime
    paper_count_7d: int
    repo_count_7d: int
    news_count_7d: int
    velocity_growth_pct: float
    hype_to_substance_ratio: float
    signal_classification: SignalClassification


class TrendsOverviewResponse(BaseModel):
    computed_at: datetime
    total_tracked_topics: int
    signal_counts: dict[str, int]
    breakthrough_momentum: List[TrendSnapshotItem]
    hype_spikes: List[TrendSnapshotItem]
    steady_adoption: List[TrendSnapshotItem]
    cooling: List[TrendSnapshotItem]
    all_snapshots: List[TrendSnapshotItem]


class TimelineEvent(BaseModel):
    document_id: str
    title: str
    content_type: str
    lifecycle_stage: str
    source_name: str
    canonical_url: str
    published_at: str
    summary: str
    is_focal_point: bool


class StoryTimelineResponse(BaseModel):
    document_id: str
    total_events: int
    consensus_status: ConsensusStatus
    consensus_summary: str
    timeline: List[TimelineEvent]

