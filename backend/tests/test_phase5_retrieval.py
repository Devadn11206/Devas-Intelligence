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
from app.modules.retrieval.query_parser import SearchRequest, sanitize_tsquery_input
from app.modules.retrieval.service import RetrievalService
from app.core.embeddings import get_embedding_service
from app.main import app

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
# 1. SANITIZED QUERY PARSER TESTS
# ==============================================================================

def test_sanitize_tsquery_special_characters():
    # Test special characters, formulas, and unbalanced quotes
    raw_query = 'C++ & PINNs/PDEs: u_t + u*u_x = 0 "unbalanced quote'
    sanitized = sanitize_tsquery_input(raw_query)

    assert '"' not in sanitized
    assert "C++" in sanitized or "C" in sanitized
    assert "PINNs/PDEs:" in sanitized or "PINNs" in sanitized


# ==============================================================================
# 2. HYBRID RRF FUSION OUTPERFORMS SINGLE-MODALITY BASELINES
# ==============================================================================

@pytest.mark.asyncio
async def test_hybrid_rrf_fusion_vs_single_mode_baselines(test_session_factory):
    async with test_session_factory() as session:
        # Create Source
        source = Source(
            name=f"Retrieval Source {uuid.uuid4().hex[:6]}",
            slug=f"retrieval-src-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        now = datetime.now(timezone.utc)
        embedder = get_embedding_service()

        query = f"DeepXDE-{uuid.uuid4().hex[:6]} physics-informed operator"

        # Doc A: Exact keyword match in abstract ("DeepXDE physics-informed neural operator"), but orthogonal vector
        uid_a = uuid.uuid4().hex[:6]
        doc_a = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uid_a}",
            canonical_url=f"https://arxiv.org/abs/2405.{uid_a}",
            content_hash=uuid.uuid4().hex,
            title="Scientific Machine Learning in Fluid Mechanics",
            summary_raw=f"We evaluate {query} benchmarks for high reynolds numbers.",
            content_raw=f"{query} benchmarks for turbulent flows.",
            authors=["Alice Fluid"],
            tags=["pinn"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=now,
        )

        # Doc B: Semantic match with different phrasing ("PINN neural solver framework"), identical vector
        uid_b = uuid.uuid4().hex[:6]
        doc_b = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uid_b}",
            canonical_url=f"https://arxiv.org/abs/2405.{uid_b}",
            content_hash=uuid.uuid4().hex,
            title="Differentiable Navier-Stokes Solvers",
            summary_raw="A novel differentiable simulation framework for partial differential equations.",
            content_raw="Simulation framework for partial differential equations.",
            authors=["Bob Navier"],
            tags=["simulation"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=now,
        )

        # Doc C: Unrelated noise
        uid_c = uuid.uuid4().hex[:6]
        doc_c = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uid_c}",
            canonical_url=f"https://arxiv.org/abs/2405.{uid_c}",
            content_hash=uuid.uuid4().hex,
            title="Ancient Roman Agricultural Accounting",
            summary_raw="Grain distribution and crop yields in imperial Rome.",
            content_raw="Ancient Roman grain economics.",
            authors=["Historian Claudia"],
            tags=["history"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=now,
        )

        session.add_all([doc_a, doc_b, doc_c])
        await session.commit()
        await session.refresh(doc_a)
        await session.refresh(doc_b)
        await session.refresh(doc_c)

        # Create Chunks
        # Query vector is derived from query
        query_vec = embedder.embed_query(query)
        # Doc B matches query vector closely (same vector)
        # Doc A and Doc C get different orthogonal vectors
        vec_a = embedder.embed_query("totally unrelated text string A")
        vec_b = query_vec
        vec_c = embedder.embed_query("totally unrelated text string C")

        chunk_a = DocumentChunk(
            document_id=doc_a.id,
            chunk_index=0,
            section_type="abstract",
            content=doc_a.summary_raw,
            token_count=15,
            embedding=vec_a,
        )
        chunk_b = DocumentChunk(
            document_id=doc_b.id,
            chunk_index=0,
            section_type="abstract",
            content=doc_b.summary_raw,
            token_count=15,
            embedding=vec_b,
        )
        chunk_c = DocumentChunk(
            document_id=doc_c.id,
            chunk_index=0,
            section_type="abstract",
            content=doc_c.summary_raw,
            token_count=15,
            embedding=vec_c,
        )

        session.add_all([chunk_a, chunk_b, chunk_c])
        await session.commit()

        service = RetrievalService(session)

        # 1. Test Hybrid Mode
        req_hybrid = SearchRequest(query=query, mode="hybrid", top_k=10)
        res_hybrid = await service.search(req_hybrid)
        hybrid_doc_ids = [r["document_id"] for r in res_hybrid["results"]]

        assert str(doc_a.id) in hybrid_doc_ids
        assert str(doc_b.id) in hybrid_doc_ids

        # 2. Test Lexical Mode alone (Finds Doc A via text match, misses Doc B)
        req_lexical = SearchRequest(query=query, mode="lexical", top_k=10)
        res_lexical = await service.search(req_lexical)
        lexical_doc_ids = [r["document_id"] for r in res_lexical["results"]]
        assert str(doc_a.id) in lexical_doc_ids
        assert str(doc_b.id) not in lexical_doc_ids

        # 3. Test Vector Mode alone (Ranks Doc B first due to vector similarity)
        req_vector = SearchRequest(query=query, mode="vector", top_k=10)
        res_vector = await service.search(req_vector)
        vector_doc_ids = [r["document_id"] for r in res_vector["results"]]
        assert str(doc_b.id) in vector_doc_ids
        assert vector_doc_ids[0] == str(doc_b.id)


# ==============================================================================
# 3. METADATA & HAS_LINKED_CODE FILTERING
# ==============================================================================

@pytest.mark.asyncio
async def test_search_has_linked_code_filtering(test_session_factory):
    async with test_session_factory() as session:
        source = Source(
            name=f"Filter Source {uuid.uuid4().hex[:6]}",
            slug=f"filter-src-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        unique_topic = f"Quantum Annealing {uuid.uuid4().hex[:6]}"

        # Paper 1: Has linked code repository
        paper_with_code = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2406.{uuid.uuid4().hex[:4]}",
            content_hash=uuid.uuid4().hex,
            title=f"{unique_topic} Implementations",
            summary_raw="Experimental evaluation with official code release.",
            authors=["Alice Quantum"],
            tags=["quantum"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        # Repo
        repo_doc = Document(
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"repo-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://github.com/lab/quantum-{uuid.uuid4().hex[:6]}",
            content_hash=uuid.uuid4().hex,
            title=f"{unique_topic} Repo",
            summary_raw="Code repository.",
            authors=["Alice Quantum"],
            tags=["quantum"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )

        # Paper 2: Standalone paper (NO linked code)
        paper_without_code = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2406.{uuid.uuid4().hex[:4]}",
            content_hash=uuid.uuid4().hex,
            title=f"{unique_topic} Theoretical Bounds",
            summary_raw="Pure theoretical proofs without code.",
            authors=["Bob Theory"],
            tags=["quantum"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )

        session.add_all([paper_with_code, repo_doc, paper_without_code])
        await session.commit()
        await session.refresh(paper_with_code)
        await session.refresh(repo_doc)
        await session.refresh(paper_without_code)

        # Create link Repo -> Paper IMPLEMENTS
        link = EntityLink(
            source_entity_id=repo_doc.id,
            target_entity_id=paper_with_code.id,
            relation_type=RelationType.IMPLEMENTS,
            confidence_score=1.0,
            link_method=LinkMethod.DETERMINISTIC_URL,
            evidence_snippet="GitHub repo implements paper",
        )
        session.add(link)

        # Create chunks with matching search vector
        embedder = get_embedding_service()
        vec = embedder.embed_query(unique_topic)

        c1 = DocumentChunk(
            document_id=paper_with_code.id,
            chunk_index=0,
            section_type="abstract",
            content=paper_with_code.summary_raw,
            token_count=10,
            embedding=vec,
        )
        c2 = DocumentChunk(
            document_id=paper_without_code.id,
            chunk_index=0,
            section_type="abstract",
            content=paper_without_code.summary_raw,
            token_count=10,
            embedding=vec,
        )
        session.add_all([c1, c2])
        await session.commit()

        service = RetrievalService(session)

        # Query with has_linked_code=True
        req_code = SearchRequest(
            query=unique_topic,
            content_types=["paper"],
            has_linked_code=True,
            top_k=10,
        )
        res_code = await service.search(req_code)
        code_doc_ids = [r["document_id"] for r in res_code["results"]]

        assert str(paper_with_code.id) in code_doc_ids
        assert str(paper_without_code.id) not in code_doc_ids


# ==============================================================================
# 4. API ENDPOINTS, CACHE HIT & AUTOCOMPLETE SUGGESTIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_search_api_caching_and_suggestions(test_session_factory):
    async with test_session_factory() as session:
        source = Source(
            name=f"API Search Source {uuid.uuid4().hex[:6]}",
            slug=f"api-search-src-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)

        topic_keyword = f"DiffusionTransformers-{uuid.uuid4().hex[:6]}"
        doc = Document(
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2407.{uuid.uuid4().hex[:4]}",
            content_hash=uuid.uuid4().hex,
            title=f"Scalable {topic_keyword} for Image Synthesis",
            summary_raw=f"We study scalable {topic_keyword} architectures.",
            authors=["Dr. DiT"],
            tags=["dit", "diffusion"],
            metadata_={},
            processing_status=ProcessingStatus.PROCESSED,
            published_at=datetime.now(timezone.utc),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        embedder = get_embedding_service()
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            section_type="abstract",
            content=doc.summary_raw,
            token_count=12,
            embedding=embedder.embed_query(topic_keyword),
        )
        session.add(chunk)
        await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Autocomplete Suggestion API test
            sugg_resp = await client.get(f"/api/v1/search/suggest?q={topic_keyword}")
            assert sugg_resp.status_code == 200
            sugg_data = sugg_resp.json()
            assert len(sugg_data) >= 1
            assert any(topic_keyword in s["title"] for s in sugg_data)

            # 2. Search POST Endpoint (First call -> Cache miss)
            search_payload = {
                "query": topic_keyword,
                "mode": "hybrid",
                "top_k": 5,
            }
            res1 = await client.post("/api/v1/search", json=search_payload)
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["cache_hit"] is False
            assert len(data1["results"]) >= 1
            assert data1["results"][0]["document_id"] == str(doc.id)

            # 3. Search POST Endpoint (Second call -> Cache hit)
            res2 = await client.post("/api/v1/search", json=search_payload)
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["cache_hit"] is True
            assert len(data2["results"]) >= 1
            assert data2["results"][0]["document_id"] == str(doc.id)

            # 4. Search GET Endpoint
            res_get = await client.get(f"/api/v1/search?q={topic_keyword}&mode=hybrid")
            assert res_get.status_code == 200
            data_get = res_get.json()
            assert len(data_get["results"]) >= 1
