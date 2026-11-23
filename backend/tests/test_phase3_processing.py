import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.db.models.intel import (
    Source,
    SourceCategory,
    Document,
    DocumentChunk,
    EventCluster,
    ContentType,
    ProcessingStatus,
)
from app.db.models.tenant import User, UserRole, Bookmark
from app.modules.processing.chunker import chunk_document, clean_text
from app.modules.processing.extractor import (
    StructuredExtractor,
    PaperExtractionSchema,
    RepoExtractionSchema,
)
from app.modules.processing.clusterer import EventClusterer
from app.modules.processing.service import ProcessingService
from app.core.llm_provider import MockLLMProvider
from app.core.embeddings import get_embedding_service
from app.core.security import create_access_token

DATABASE_URL = "postgresql+asyncpg://deva_user:deva_password@localhost:5433/deva_test"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


# ==============================================================================
# 1. TEXT CHUNKING & HYBRID INDEXING TESTS
# ==============================================================================

def test_clean_text_and_chunker_provenance():
    sample_dirty_text = """
    <html><body>
    <h1>Physics-Informed Deep Learning</h1>
    <p>We present a novel neural operator framework for Navier-Stokes equations.</p>
    ## Methodology
    Our model optimizes loss over both boundary conditions and residual collocation points.
    ## Results
    Achieved 42x speedup compared to standard finite volume solvers.
    </body></html>
    """
    cleaned = clean_text(sample_dirty_text)
    assert "<html>" not in cleaned
    assert "Physics-Informed Deep Learning" in cleaned

    chunks = chunk_document(
        title="Physics-Informed Deep Learning",
        summary_raw="We present a novel neural operator framework.",
        content_raw=cleaned,
        content_type="paper",
    )

    assert len(chunks) >= 2
    # Verify section provenance tagging
    section_types = [c.section_type for c in chunks]
    assert "abstract" in section_types
    assert any(s in section_types for s in ["methodology", "results", "article_body"])
    assert all(c.token_count > 0 for c in chunks)


@pytest.mark.asyncio
async def test_processing_creates_chunks_with_vectors_and_tsvector(test_session_factory):
    async with test_session_factory() as session:
        # Seed Source
        source = Source(
            name=f"arXiv Processing Source {uuid.uuid4().hex[:6]}",
            slug=f"arxiv-proc-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://export.arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        # Seed Raw Document
        doc = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"2401.{uuid.uuid4().hex[:5]}",
            canonical_url=f"https://arxiv.org/abs/2401.{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="Mesh-Free Neural Solvers for High Reynolds Aerodynamics",
            summary_raw="This paper introduces a mesh-free continuous operator for transonic airflow.",
            content_raw="# Methodology\nCollocation points are sampled dynamically.\n# Results\nSuperior convergence on NACA 0012 aerofoil.",
            authors=["Dr. Euler", "Dr. Navier"],
            tags=["aerodynamics", "sciml"],
            processing_status=ProcessingStatus.RAW_INGESTED,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        # Execute Processing
        service = ProcessingService(llm_provider=MockLLMProvider())
        processed_doc = await service.process_document(session, doc.id)

        assert processed_doc.processing_status == ProcessingStatus.PROCESSED
        assert processed_doc.processed_at is not None

        # Verify chunks created in DB
        chunks_res = await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
        )
        chunks = chunks_res.scalars().all()
        assert len(chunks) >= 1

        # Check hybrid indexing: tsvector is generated and embedding vector is 768-dim
        first_chunk = chunks[0]
        assert first_chunk.embedding is not None
        assert len(first_chunk.embedding) == 768
        assert first_chunk.search_vector is not None


# ==============================================================================
# 2. FACT VS AI SEPARATION TEST (MODULE 2 RULE)
# ==============================================================================

@pytest.mark.asyncio
async def test_fact_vs_ai_separation_integrity(test_session_factory):
    async with test_session_factory() as session:
        source = Source(
            name=f"GitHub Source {uuid.uuid4().hex[:6]}",
            slug=f"gh-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.CODE,
            adapter_key="github",
            base_url="https://github.com",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        original_summary = "An immutable scientific python library for PDE solving."
        original_metadata = {"stars": 1250, "language": "Python"}

        doc = Document(
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"repo-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://github.com/deva/pde-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title="pde-solver-torch",
            summary_raw=original_summary,
            content_raw="README: Fast GPU accelerated solver.",
            metadata_=original_metadata,
            processing_status=ProcessingStatus.RAW_INGESTED,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        service = ProcessingService(llm_provider=MockLLMProvider())
        processed = await service.process_document(session, doc.id)

        # STRICT FACT PRESERVATION CHECK:
        # summary_raw and metadata must remain completely unmodified
        assert processed.summary_raw == original_summary
        assert processed.metadata_ == original_metadata

        # summary_ai MUST be populated with structured fields
        assert processed.summary_ai is not None
        assert "core_purpose" in processed.summary_ai or "problem_statement" in processed.summary_ai or "executive_summary" in processed.summary_ai


# ==============================================================================
# 3. EVENT CLUSTERING & DEDUPLICATION TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_event_clustering_groups_near_identical_events(test_session_factory):
    async with test_session_factory() as session:
        source1 = Source(
            name=f"News Source A {uuid.uuid4().hex[:6]}",
            slug=f"news-a-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.TECH_NEWS,
            adapter_key="rss",
            base_url="https://sourcea.com",
            config={},
        )
        source2 = Source(
            name=f"News Source B {uuid.uuid4().hex[:6]}",
            slug=f"news-b-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.COMPANY_BLOG,
            adapter_key="rss",
            base_url="https://sourceb.com",
            config={},
        )
        session.add_all([source1, source2])
        await session.commit()

        # Doc 1: Release announcement from Source A
        title1 = f"Anthropic Releases Claude 3.5 Sonnet With Enhanced Coding Velocity {uuid.uuid4().hex[:4]}"
        summary1 = "Anthropic announces the public release of Claude 3.5 Sonnet featuring major coding benchmarks improvements."
        doc1 = Document(
            source_id=source1.id,
            content_type=ContentType.ARTICLE,
            external_id=f"art-1-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://sourcea.com/claude-release-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title=title1,
            summary_raw=summary1,
            processing_status=ProcessingStatus.RAW_INGESTED,
        )

        # Doc 2: Near-identical announcement from Source B covering the exact same event
        title2 = title1  # Same story title
        summary2 = summary1  # Same story summary
        doc2 = Document(
            source_id=source2.id,
            content_type=ContentType.ARTICLE,
            external_id=f"art-2-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://sourceb.com/claude-release-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title=title2,
            summary_raw=summary2,
            processing_status=ProcessingStatus.RAW_INGESTED,
        )

        # Doc 3: Completely unrelated paper
        doc3 = Document(
            source_id=source1.id,
            content_type=ContentType.PAPER,
            external_id=f"art-3-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/quantum-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title=f"Quantum Entanglement in Superconducting Topological Qubits {uuid.uuid4().hex[:4]}",
            summary_raw="We present quantum coherence measurements in braided Majorana zero modes.",
            processing_status=ProcessingStatus.RAW_INGESTED,
        )

        session.add_all([doc1, doc2, doc3])
        await session.commit()

        service = ProcessingService(llm_provider=MockLLMProvider())
        p_doc1 = await service.process_document(session, doc1.id)
        p_doc2 = await service.process_document(session, doc2.id)
        p_doc3 = await service.process_document(session, doc3.id)

        # Verify Doc 1 and Doc 2 share the same event_cluster_id
        assert p_doc1.event_cluster_id is not None
        assert p_doc2.event_cluster_id is not None
        assert p_doc1.event_cluster_id == p_doc2.event_cluster_id

        # Verify Cluster document_count is 2
        cluster_res = await session.execute(
            select(EventCluster).where(EventCluster.id == p_doc1.event_cluster_id)
        )
        cluster = cluster_res.scalars().first()
        assert cluster is not None
        assert cluster.document_count == 2

        # Verify Unrelated Doc 3 is assigned to a separate cluster
        assert p_doc3.event_cluster_id is not None
        assert p_doc3.event_cluster_id != p_doc1.event_cluster_id


# ==============================================================================
# 4. END-TO-END FEED & DOCUMENT DETAIL API TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_intelligence_feed_and_document_detail_api(client, test_session_factory):
    # 1. Fetch clustered feed
    feed_res = await client.get("/api/v1/intel/feed?limit=10")
    assert feed_res.status_code == 200
    feed_cards = feed_res.json()
    assert isinstance(feed_cards, list)
    assert len(feed_cards) >= 1

    first_card = feed_cards[0]
    assert "primary_document_id" in first_card
    assert "corroborating_sources" in first_card
    doc_id = first_card["primary_document_id"]

    # 2. Fetch full document details
    detail_res = await client.get(f"/api/v1/intel/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "document" in detail
    assert "chunk_count" in detail
    assert "cluster_siblings" in detail
    assert detail["document"]["id"] == doc_id
