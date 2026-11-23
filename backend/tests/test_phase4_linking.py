import os
os.environ["TESTING"] = "True"
os.environ["ENVIRONMENT"] = "test"
import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.db.models.intel import (
    Source,
    SourceCategory,
    Document,
    DocumentChunk,
    ContentType,
    ProcessingStatus,
    EntityLink,
    RelationType,
    LinkMethod,
)
from app.db.models.tenant import User, UserRole
from app.modules.linking.extractors import (
    extract_github_urls,
    extract_arxiv_ids,
    normalize_github_url,
    normalize_arxiv_id,
)
from app.modules.linking.linker import EntityLinkerService
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
# 1. EXTRACTOR & NORMALIZATION UNIT TESTS
# ==============================================================================

def test_extract_and_normalize_github_urls():
    text = """
    Check out our implementation at https://github.com/google-deepmind/graphcast.git and
    also https://github.com/facebookresearch/llama/blob/main/README.md for reproduction.
    """
    urls = extract_github_urls(text)
    assert len(urls) == 2
    assert "https://github.com/google-deepmind/graphcast" in urls
    assert "https://github.com/facebookresearch/llama" in urls


def test_extract_and_normalize_arxiv_ids():
    text = """
    As shown in arXiv:2303.08774v2 and also [2106.09685], LoRA reduces trainable parameters.
    See https://arxiv.org/abs/2401.12345 for details.
    """
    ids = extract_arxiv_ids(text)
    assert "2303.08774" in ids
    assert "2106.09685" in ids
    assert "2401.12345" in ids


# ==============================================================================
# 2. THREE-PASS HYBRID ENTITY LINKING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_pass1_deterministic_url_linking(test_session_factory):
    async with test_session_factory() as session:
        # Create Source
        source = Source(
            name=f"Linker Source {uuid.uuid4().hex[:6]}",
            slug=f"linker-src-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        # 1. Seed target repo
        target_repo_url = f"https://github.com/deva-intel/fast-diffusion-{uuid.uuid4().hex[:6]}"
        repo_doc = Document(
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"repo-{uuid.uuid4().hex[:6]}",
            canonical_url=target_repo_url,
            content_hash=uuid.uuid4().hex,
            title="Fast Diffusion PyTorch Implementation",
            summary_raw="Official repository for Fast Diffusion.",
            content_raw="Code implementation of Fast Diffusion.",
            authors=["Alice Developer"],
            tags=["diffusion", "pytorch"],
            metadata_={"stars": 500},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        session.add(repo_doc)
        await session.commit()
        await session.refresh(repo_doc)

        # 2. Seed paper mentioning repo in summary_raw
        paper_doc = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2401.{uuid.uuid4().hex[:4]}",
            content_hash=uuid.uuid4().hex,
            title="Fast Diffusion: High-Fidelity Sampling in 4 Steps",
            summary_raw=f"We propose Fast Diffusion. Code available at {target_repo_url}.",
            content_raw=f"Full details and code at {target_repo_url}",
            authors=["Dr. Alice", "Dr. Bob"],
            tags=["diffusion", "machine-learning"],
            metadata_={"arxiv_id": f"2401.{uuid.uuid4().hex[:4]}"},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        session.add(paper_doc)
        await session.commit()
        await session.refresh(paper_doc)

        # Run entity linker
        linker = EntityLinkerService(session)
        created_links = await linker.link_document(paper_doc)

        assert len(created_links) >= 1
        link = created_links[0]
        # Repo implements Paper (source: repo, target: paper)
        assert link.source_entity_id == repo_doc.id
        assert link.target_entity_id == paper_doc.id
        assert link.relation_type == RelationType.IMPLEMENTS
        assert link.confidence_score == 1.0
        assert link.link_method == LinkMethod.DETERMINISTIC_URL


@pytest.mark.asyncio
async def test_pass1_arxiv_id_linking(test_session_factory):
    async with test_session_factory() as session:
        # Create Source
        source = Source(
            name=f"Linker Source 2 {uuid.uuid4().hex[:6]}",
            slug=f"linker-src2-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.CODE,
            adapter_key="github",
            base_url="https://github.com",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        # 1. Seed paper with numeric arXiv ID
        import random
        rand_num = random.randint(10000, 99999)
        arxiv_id = f"2402.{rand_num}"
        paper_doc = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"arxiv-{arxiv_id}",
            canonical_url=f"https://arxiv.org/abs/{arxiv_id}",
            content_hash=uuid.uuid4().hex,
            title="Quantum Neural Operators for PDEs",
            summary_raw="We formulate quantum circuits for operator learning.",
            authors=["Charlie Quantum", "Dave Smith"],
            tags=["quantum", "pde"],
            metadata_={"arxiv_id": arxiv_id},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        session.add(paper_doc)
        await session.commit()
        await session.refresh(paper_doc)

        # 2. Seed repo citing arXiv ID in README content
        repo_doc = Document(
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"repo-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://github.com/lab/qno-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title="QNO: Quantum Neural Operators",
            summary_raw="PyTorch code for QNO.",
            content_raw=f"Please cite our work: arXiv:{arxiv_id} [cs.LG]",
            authors=["Charlie Quantum"],
            tags=["quantum", "pytorch"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        session.add(repo_doc)
        await session.commit()
        await session.refresh(repo_doc)

        # Run entity linker on repo
        linker = EntityLinkerService(session)
        created_links = await linker.link_document(repo_doc)

        assert len(created_links) >= 1
        link = created_links[0]
        assert link.source_entity_id == repo_doc.id
        assert link.target_entity_id == paper_doc.id
        assert link.relation_type == RelationType.IMPLEMENTS
        assert link.confidence_score == 1.0
        assert link.link_method == LinkMethod.ARXIV_ID_MATCH


@pytest.mark.asyncio
async def test_pass3_semantic_author_overlap_linking(test_session_factory):
    async with test_session_factory() as session:
        source = Source(
            name=f"Linker Source 3 {uuid.uuid4().hex[:6]}",
            slug=f"linker-src3-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        now = datetime.now(timezone.utc)

        # Seed paper with unique title
        shared_title = f"FlashMoE Sparse Mixture of Experts {uuid.uuid4().hex[:6]}"
        paper_doc = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"arxiv-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2403.{uuid.uuid4().hex[:4]}",
            content_hash=uuid.uuid4().hex,
            title=shared_title,
            summary_raw="Efficient sparse MoE routing algorithm with kernel optimizations.",
            authors=["Elena Rostova", "Marcus Vance"],
            tags=["moe", "llm"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=now - timedelta(days=10),
        )
        session.add(paper_doc)
        await session.commit()
        await session.refresh(paper_doc)

        # Seed repo with similar content and overlapping author surname "Rostova"
        repo_doc = Document(
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"gh-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://github.com/moe-lab/flashmoe-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title=shared_title,
            summary_raw="Efficient sparse MoE routing algorithm with kernel optimizations.",
            authors=["E. Rostova", "Dev Contributor"],
            tags=["moe", "cuda"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=now,
        )
        session.add(repo_doc)
        await session.commit()
        await session.refresh(repo_doc)

        # Ensure chunks with mock embeddings exist for Pass 3
        from app.core.embeddings import get_embedding_service
        embedder = get_embedding_service()
        vec_paper = embedder.embed_query(shared_title)
        vec_repo = embedder.embed_query(shared_title)

        chunk_paper = DocumentChunk(
            document_id=paper_doc.id,
            chunk_index=0,
            section_type="abstract",
            content=paper_doc.summary_raw,
            token_count=20,
            embedding=vec_paper,
        )
        chunk_repo = DocumentChunk(
            document_id=repo_doc.id,
            chunk_index=0,
            section_type="readme",
            content=repo_doc.summary_raw,
            token_count=20,
            embedding=vec_repo,
        )
        session.add_all([chunk_paper, chunk_repo])
        await session.commit()

        linker = EntityLinkerService(session)
        created_links = await linker.link_document(repo_doc)

        assert len(created_links) >= 1
        link = created_links[0]
        assert link.relation_type == RelationType.IMPLEMENTS
        assert link.link_method == LinkMethod.SEMANTIC_AUTHOR_MATCH
        assert link.confidence_score >= 0.72


# ==============================================================================
# 3. API ENDPOINTS & SUBGRAPH VERIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_subgraph_and_links_api_endpoints(test_session_factory):
    async with test_session_factory() as session:
        # Create Admin User
        admin = User(
            email=f"admin_linker_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="pw",
            full_name="Admin Linker",
            role=UserRole.PLATFORM_ADMIN,
            is_active=True,
            is_verified=True,
        )
        session.add(admin)

        source = Source(
            name=f"API Linker Source {uuid.uuid4().hex[:6]}",
            slug=f"api-linker-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(admin)
        await session.refresh(source)

        token = create_access_token(admin.id, admin.role.value)

        # Create Paper, Repo, and Link
        uid = uuid.uuid4().hex[:6]
        paper = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uid}",
            canonical_url=f"https://arxiv.org/abs/2405.{uid}",
            content_hash=uuid.uuid4().hex,
            title="Graph Representation Learning",
            summary_raw="Deep graph neural networks overview.",
            authors=["Prof. Graph"],
            tags=["gnn"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        repo = Document(
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"repo-{uid}",
            canonical_url=f"https://github.com/gnn-lab/gnn-core-{uid}",
            content_hash=uuid.uuid4().hex,
            title="GNN Core PyTorch Library",
            summary_raw="Graph neural networks library.",
            authors=["Prof. Graph"],
            tags=["gnn", "pytorch"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        session.add_all([paper, repo])
        await session.commit()
        await session.refresh(paper)
        await session.refresh(repo)

        link = EntityLink(
            source_entity_id=paper.id,
            target_entity_id=repo.id,
            relation_type=RelationType.IMPLEMENTS,
            confidence_score=1.0,
            link_method=LinkMethod.DETERMINISTIC_URL,
            evidence_snippet="https://github.com/gnn-lab/gnn-core",
        )
        session.add(link)
        await session.commit()

        from app.main import app
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Test /documents/{id}/links
            links_resp = await client.get(f"/api/v1/intel/documents/{paper.id}/links")
            assert links_resp.status_code == 200
            links_data = links_resp.json()
            assert len(links_data) == 1
            assert links_data[0]["relation_type"] == "IMPLEMENTS"
            assert links_data[0]["direction"] == "outgoing"
            assert links_data[0]["linked_document"]["id"] == str(repo.id)

            # 2. Test /documents/{id}/graph?depth=2
            graph_resp = await client.get(f"/api/v1/intel/documents/{paper.id}/graph?depth=2")
            assert graph_resp.status_code == 200
            graph_data = graph_resp.json()
            assert graph_data["root_document_id"] == str(paper.id)
            assert len(graph_data["nodes"]) >= 2
            assert len(graph_data["edges"]) >= 1
            assert any(n["is_root"] is True for n in graph_data["nodes"])

            # 3. Test admin linking stats
            stats_resp = await client.get(
                "/api/v1/admin/linking/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert stats_resp.status_code == 200
            stats_data = stats_resp.json()
            assert stats_data["total_links"] >= 1
            assert "IMPLEMENTS" in stats_data["by_relation_type"]
