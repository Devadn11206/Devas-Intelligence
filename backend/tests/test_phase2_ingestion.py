import uuid
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.db.models.intel import (
    Source,
    SourceCategory,
    SourceHealthStatus,
    IngestionJob,
    IngestionJobStatus,
    QuarantinedRecord,
    Document,
    ContentType,
    ProcessingStatus,
)
from app.db.models.tenant import User, UserRole, AuditLog
from app.modules.ingestion.base import AdapterRegistry, CanonicalRecord
from app.modules.ingestion.adapters.arxiv import ArxivAdapter
from app.modules.ingestion.adapters.github import GitHubAdapter
from app.modules.ingestion.adapters.huggingface import HuggingFaceAdapter
from app.modules.ingestion.adapters.semantic_scholar import SemanticScholarAdapter
from app.modules.ingestion.adapters.rss import RSSAdapter
from app.modules.ingestion.service import IngestionService, seed_default_sources
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
# 1. ADAPTER PARSING & VALIDATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_arxiv_adapter_parsing_and_normalization():
    sample_atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2301.00001v1</id>
            <title>Physics-Informed Neural Networks for High Reynolds Numbers</title>
            <summary>A detailed study of PINNs in turbulent fluid mechanics.</summary>
            <author><name>Jane Doe</name></author>
            <author><name>John Smith</name></author>
            <category term="cs.LG" />
            <category term="math.NA" />
            <published>2023-01-01T12:00:00Z</published>
        </entry>
    </feed>"""

    adapter = ArxivAdapter()
    parsed = adapter.parse([{"raw_xml": sample_atom_xml}])
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Physics-Informed Neural Networks for High Reynolds Numbers"

    mock_source = Source(
        id=uuid.uuid4(),
        name="arXiv Test",
        slug="arxiv-test",
        category=SourceCategory.RESEARCH,
        adapter_key="arxiv",
        base_url="https://export.arxiv.org",
        config={},
    )
    records = adapter.normalize(parsed, mock_source)
    assert len(records) == 1
    valid, quarantined = adapter.validate(records)
    assert len(valid) == 1
    assert len(quarantined) == 0
    assert valid[0].content_type == ContentType.PAPER
    assert "cs.LG" in valid[0].tags
    assert "Jane Doe" in valid[0].authors


@pytest.mark.asyncio
async def test_github_adapter_parsing_and_normalization():
    sample_gh_items = [
        {
            "id": 123456,
            "name": "deepxde",
            "full_name": "luluxingstudy/deepxde",
            "html_url": "https://github.com/luluxingstudy/deepxde",
            "description": "Deep learning library for solving differential equations",
            "stargazers_count": 5200,
            "forks_count": 1100,
            "language": "Python",
            "topics": ["deep-learning", "pde", "pinns"],
            "owner": {"login": "luluxingstudy"},
            "license": {"spdx_id": "LGPL-2.1"},
            "created_at": "2019-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z",
        }
    ]

    adapter = GitHubAdapter()
    parsed = adapter.parse(sample_gh_items)
    mock_source = Source(
        id=uuid.uuid4(),
        name="GitHub SciML",
        slug="github-sciml",
        category=SourceCategory.CODE,
        adapter_key="github",
        base_url="https://api.github.com",
        config={},
    )
    records = adapter.normalize(parsed, mock_source)
    assert len(records) == 1
    assert records[0].content_type == ContentType.REPO
    assert records[0].metadata["stars"] == 5200


@pytest.mark.asyncio
async def test_adapter_quarantine_malformed_records():
    adapter = RSSAdapter()
    malformed = [
        {"title": "", "canonical_url": "not-valid-url"},
    ]
    valid, quarantined = adapter.validate(malformed)
    assert len(valid) == 0
    assert len(quarantined) == 1
    assert "validation_error" in quarantined[0]


# ==============================================================================
# 2. INGESTION PIPELINE & IDEMPOTENCY EXIT-GATE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_idempotent_ingestion_pipeline(test_session_factory):
    async with test_session_factory() as test_db_session:
        unique_slug = f"arxiv-test-idem-{uuid.uuid4().hex[:6]}"
        source = Source(
            name=f"arXiv Idempotency Source {unique_slug}",
            slug=unique_slug,
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://export.arxiv.org/api/query",
            config={"query": "test"},
        )
        test_db_session.add(source)
        await test_db_session.commit()
        await test_db_session.refresh(source)

        sample_atom_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/2401.{uuid.uuid4().hex[:5]}v1</id>
                <title>Idempotent Deep Learning</title>
                <summary>Original Abstract Body.</summary>
                <author><name>Alice</name></author>
                <category term="cs.AI" />
                <published>2024-01-01T00:00:00Z</published>
            </entry>
        </feed>"""

        transport = httpx.MockTransport(lambda req: httpx.Response(200, text=sample_atom_xml))
        async with httpx.AsyncClient(transport=transport) as mock_client:
            # Run 1: First ingestion run (expect 1 insert)
            job1 = await IngestionService.run_source_ingestion(
                db=test_db_session, source_id=source.id, triggered_by="test", client=mock_client
            )
            assert job1.status == IngestionJobStatus.COMPLETED
            assert job1.records_inserted == 1
            assert job1.records_updated == 0

            # Run 2: Exact same feed content (expect 0 insert, 0 update)
            job2 = await IngestionService.run_source_ingestion(
                db=test_db_session, source_id=source.id, triggered_by="test", client=mock_client
            )
            assert job2.status == IngestionJobStatus.COMPLETED
            assert job2.records_inserted == 0
            assert job2.records_updated == 0

        # Run 3: Content changed (updated summary) -> (expect 0 insert, 1 update)
        mutated_atom_xml = sample_atom_xml.replace("Original Abstract Body.", "Updated and Revised Abstract.")
        transport_mutated = httpx.MockTransport(lambda req: httpx.Response(200, text=mutated_atom_xml))
        async with httpx.AsyncClient(transport=transport_mutated) as mock_client2:
            job3 = await IngestionService.run_source_ingestion(
                db=test_db_session, source_id=source.id, triggered_by="test", client=mock_client2
            )
            assert job3.status == IngestionJobStatus.COMPLETED
            assert job3.records_inserted == 0
            assert job3.records_updated == 1


@pytest.mark.asyncio
async def test_failure_isolation_and_quarantine(test_session_factory):
    async with test_session_factory() as test_db_session:
        unique_slug = f"failing-source-{uuid.uuid4().hex[:6]}"
        source = Source(
            name=f"Failing Source Test {unique_slug}",
            slug=unique_slug,
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://export.arxiv.org/api/query",
            config={"query": "test"},
        )
        test_db_session.add(source)
        await test_db_session.commit()
        await test_db_session.refresh(source)

        transport_error = httpx.MockTransport(lambda req: httpx.Response(500, text="Internal Server Error"))
        async with httpx.AsyncClient(transport=transport_error) as mock_client:
            job = await IngestionService.run_source_ingestion(
                db=test_db_session, source_id=source.id, triggered_by="test", client=mock_client
            )
            assert job.status == IngestionJobStatus.FAILED
            assert "500" in (job.error_summary or "")

            await test_db_session.refresh(source)
            assert source.health_status == SourceHealthStatus.FAILING
            assert source.last_error is not None


# ==============================================================================
# 3. ADMIN API, RBAC & AUDIT LOGGING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_source_management_rbac(client, test_session_factory):
    async with test_session_factory() as test_db_session:
        user = User(
            email=f"dev_user_{uuid.uuid4().hex[:6]}@deva.intel",
            full_name="Regular Test User",
            role=UserRole.USER,
            is_active=True,
        )
        admin = User(
            email=f"platform_admin_{uuid.uuid4().hex[:6]}@deva.intel",
            full_name="Platform Admin User",
            role=UserRole.PLATFORM_ADMIN,
            is_active=True,
        )
        test_db_session.add_all([user, admin])
        await test_db_session.commit()
        await test_db_session.refresh(user)
        await test_db_session.refresh(admin)

        user_token = create_access_token(subject=str(user.id), role=user.role.value)
        admin_token = create_access_token(subject=str(admin.id), role=admin.role.value)

        # 1. Non-admin user denied (403)
        res_denied = await client.get(
            "/api/v1/admin/sources",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res_denied.status_code == 403

        # 2. Admin user allowed (200)
        res_allowed = await client.get(
            "/api/v1/admin/sources",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_allowed.status_code == 200
        sources = res_allowed.json()
        assert isinstance(sources, list)
        assert len(sources) >= 1

        # 3. Create new source as admin & verify audit log
        new_src_payload = {
            "name": f"Custom SciML RSS {uuid.uuid4().hex[:6]}",
            "slug": f"custom-rss-{uuid.uuid4().hex[:6]}",
            "category": "company_blog",
            "adapter_key": "rss",
            "base_url": "https://blog.deva.intel/feed.xml",
            "config": {"feed_url": "https://blog.deva.intel/feed.xml"},
            "refresh_interval_minutes": 120,
            "rate_limit_rpm": 20,
        }
        create_res = await client.post(
            "/api/v1/admin/sources",
            json=new_src_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_res.status_code == 201
        created_id = create_res.json()["id"]

        audit_res = await test_db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "admin_create_source",
                AuditLog.resource_id == created_id,
            )
        )
        audit_entry = audit_res.scalars().first()
        assert audit_entry is not None
        assert audit_entry.actor_user_id == admin.id


@pytest.mark.asyncio
async def test_public_intel_documents_endpoint(client):
    res = await client.get("/api/v1/intel/documents?limit=10")
    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)
