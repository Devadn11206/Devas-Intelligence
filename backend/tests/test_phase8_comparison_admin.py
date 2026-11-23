import os
os.environ["TESTING"] = "True"
os.environ["ENVIRONMENT"] = "test"
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.models.tenant import User, UserRole
from app.db.models.intel import Document, Source, SourceCategory, ContentType, ProcessingStatus, AgentRun
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


@pytest.mark.asyncio
async def test_comparator_api_validation_and_synthesis(test_session_factory):
    """Verifies POST /api/v1/intel/compare validation and matrix generation."""
    async with test_session_factory() as session:
        # Create test source
        source = Source(
            id=uuid.uuid4(),
            name=f"Comp Source {uuid.uuid4().hex[:6]}",
            slug=f"comp-src-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.flush()

        # Create 3 documents
        doc1 = Document(
            id=uuid.uuid4(),
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"doc1-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2601.{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="Fast Attention via Speculative Token Prefetching",
            summary_raw="Low-latency speculative token prefetching for transformer decoding.",
            summary_ai={
                "methodology": "Speculative token tree prefetching with KV cache compression",
                "datasets_used": ["GSM8K", "HumanEval"],
                "reported_metrics": {"throughput_tok_s": 145.2, "latency_reduction": "42%"},
            },
            published_at=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PROCESSED,
        )
        doc2 = Document(
            id=uuid.uuid4(),
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"doc2-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://github.com/vllm/fast-decode-{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="vllm-speculative-prefetch",
            summary_raw="Open-source CUDA kernel implementation for speculative decoding.",
            summary_ai={
                "methodology": "Fused GPU kernels and asynchronous scheduling",
                "datasets_used": ["ShareGPT"],
                "reported_metrics": {"gpu_utilization": "98%"},
            },
            published_at=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PROCESSED,
        )
        doc3 = Document(
            id=uuid.uuid4(),
            source_id=source.id,
            content_type=ContentType.MODEL,
            external_id=f"doc3-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://huggingface.co/models/spec-draft-{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="spec-draft-7b-v1",
            summary_raw="Pre-trained lightweight drafting model for speculative decoding.",
            published_at=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PROCESSED,
        )
        session.add_all([doc1, doc2, doc3])
        await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            # 1. Test validation error with 1 document (should return 422)
            res_invalid = await ac.post("/api/v1/intel/compare", json={"document_ids": [str(doc1.id)]})
            assert res_invalid.status_code == 422

            # 2. Test validation error with 5 documents (should return 422)
            dummy_ids = [str(uuid.uuid4()) for _ in range(5)]
            res_invalid_5 = await ac.post("/api/v1/intel/compare", json={"document_ids": dummy_ids})
            assert res_invalid_5.status_code == 422

            # 3. Test successful comparison with 2 documents
            res_comp = await ac.post(
                "/api/v1/intel/compare",
                json={"document_ids": [str(doc1.id), str(doc2.id)]},
            )
            assert res_comp.status_code == 200
            data = res_comp.json()
            assert len(data["items"]) == 2
            assert "executive_verdict" in data
            assert len(data["comparison_rows"]) >= 4
            assert "markdown_export" in data
            assert "| Attribute |" in data["markdown_export"]


@pytest.mark.asyncio
async def test_admin_observability_endpoints_rbac(test_session_factory):
    """Verifies RBAC and telemetry on /admin/overview, /admin/agent-runs, /admin/system-health."""
    async with test_session_factory() as session:
        # Create normal user and admin user
        normal_user = User(
            id=uuid.uuid4(),
            email=f"normal-{uuid.uuid4().hex[:6]}@devaintelligence.local",
            full_name="Normal User",
            role=UserRole.USER,
        )
        admin_user = User(
            id=uuid.uuid4(),
            email=f"admin-{uuid.uuid4().hex[:6]}@devaintelligence.local",
            full_name="Admin User",
            role=UserRole.PLATFORM_ADMIN,
        )
        session.add_all([normal_user, admin_user])
        await session.commit()

        normal_token = create_access_token(subject=str(normal_user.id), role=normal_user.role.value)
        admin_token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)

        normal_headers = {"Authorization": f"Bearer {normal_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            # 1. Non-admin access should be forbidden (403)
            res_overview_forbidden = await ac.get("/api/v1/admin/overview", headers=normal_headers)
            assert res_overview_forbidden.status_code == 403

            res_runs_forbidden = await ac.get("/api/v1/admin/agent-runs", headers=normal_headers)
            assert res_runs_forbidden.status_code == 403

            res_health_forbidden = await ac.get("/api/v1/admin/system-health", headers=normal_headers)
            assert res_health_forbidden.status_code == 403

            # 2. Admin access should succeed (200)
            res_overview = await ac.get("/api/v1/admin/overview", headers=admin_headers)
            assert res_overview.status_code == 200
            ov_data = res_overview.json()
            assert "total_users" in ov_data
            assert "total_documents" in ov_data
            assert "sources_summary" in ov_data

            res_runs = await ac.get("/api/v1/admin/agent-runs", headers=admin_headers)
            assert res_runs.status_code == 200
            assert isinstance(res_runs.json(), list)

            res_health = await ac.get("/api/v1/admin/system-health", headers=admin_headers)
            assert res_health.status_code == 200
            h_data = res_health.json()
            assert "database" in h_data
            assert "pgvector_hnsw" in h_data
            assert "redis" in h_data
            assert "celery_queues" in h_data
