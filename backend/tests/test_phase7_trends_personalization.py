import os
os.environ["TESTING"] = "True"
os.environ["ENVIRONMENT"] = "test"
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.models.tenant import User, UserRole, SemanticWatchlist, Notification
from app.db.models.intel import (
    Document,
    ContentType,
    ProcessingStatus,
    Source,
    SourceCategory,
    TrendSnapshot,
    SignalClassification,
    ConsensusStatus,
    EventCluster,
)
from app.core.security import create_access_token
from app.modules.trends.calculator import TrendService, calculate_signal
from app.modules.trends.timeline import get_story_timeline
from app.modules.personalization.engine import PersonalizationEngine, cosine_similarity

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
async def test_signal_classification_formula():
    """Verify PRD Module 7 signal classification rules."""
    # Hype spike: news / substance >= 2.0 and news >= 2
    assert calculate_signal(paper_count=0, repo_count=1, news_count=3, velocity_growth_pct=10.0, hype_ratio=3.0) == SignalClassification.HYPE_SPIKE

    # Cooling: growth < -15%
    assert calculate_signal(paper_count=2, repo_count=2, news_count=1, velocity_growth_pct=-25.0, hype_ratio=0.25) == SignalClassification.COOLING

    # Breakthrough momentum: substance >= 3 and growth >= 20%
    assert calculate_signal(paper_count=3, repo_count=2, news_count=2, velocity_growth_pct=40.0, hype_ratio=0.4) == SignalClassification.BREAKTHROUGH_MOMENTUM

    # Steady adoption
    assert calculate_signal(paper_count=1, repo_count=1, news_count=1, velocity_growth_pct=5.0, hype_ratio=0.5) == SignalClassification.STEADY_ADOPTION


@pytest.mark.asyncio
async def test_trends_calculator_and_api(test_session_factory):
    """Test TrendService snapshot calculation and GET /api/v1/trends/overview."""
    async with test_session_factory() as session:
        # Create test source
        source = Source(
            id=uuid.uuid4(),
            name=f"Trend Test Source {uuid.uuid4().hex[:6]}",
            slug=f"trend-test-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.RESEARCH,
            adapter_key="arxiv",
            base_url="https://arxiv.org",
            config={},
        )
        session.add(source)
        await session.flush()

        # Create documents with common tags
        now = datetime.now(timezone.utc)
        d1 = Document(
            id=uuid.uuid4(),
            source_id=source.id,
            content_type=ContentType.PAPER,
            external_id=f"paper-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://arxiv.org/abs/2601.{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="Diffusion Transformers for Quantum Chemistry",
            summary_raw="Novel diffusion formulation for Hamiltonian simulation.",
            tags=["diffusion", "quantum", "chemistry"],
            published_at=now - timedelta(days=2),
            processing_status=ProcessingStatus.PROCESSED,
        )
        d2 = Document(
            id=uuid.uuid4(),
            source_id=source.id,
            content_type=ContentType.REPO,
            external_id=f"repo-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://github.com/test/diff-quantum-{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="open-diffusion-quantum",
            summary_raw="Code implementation of quantum diffusion transformer.",
            tags=["diffusion", "quantum", "open-source"],
            published_at=now - timedelta(days=1),
            processing_status=ProcessingStatus.PROCESSED,
        )
        session.add_all([d1, d2])
        await session.commit()

        # Calculate daily snapshots
        snapshots = await TrendService.compute_daily_snapshots(session, target_date=now)
        await session.commit()
        assert len(snapshots) >= 1

        # Test API
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            res = await ac.get("/api/v1/trends/overview")
            assert res.status_code == 200
            data = res.json()
            assert "total_tracked_topics" in data
            assert "signal_counts" in data
            assert "all_snapshots" in data


@pytest.mark.asyncio
async def test_story_evolution_timeline(test_session_factory):
    """Test story evolution timeline and consensus radar analysis."""
    async with test_session_factory() as session:
        source = Source(
            id=uuid.uuid4(),
            name=f"Timeline Source {uuid.uuid4().hex[:6]}",
            slug=f"timeline-{uuid.uuid4().hex[:6]}",
            category=SourceCategory.TECH_NEWS,
            adapter_key="rss",
            base_url="https://tech.com",
            config={},
        )
        session.add(source)
        await session.flush()

        # Create event cluster
        cluster = EventCluster(
            id=uuid.uuid4(),
            canonical_title="Breakthrough Optical Computing Interconnect",
            document_count=2,
        )
        session.add(cluster)
        await session.flush()

        now = datetime.now(timezone.utc)
        doc = Document(
            id=uuid.uuid4(),
            source_id=source.id,
            event_cluster_id=cluster.id,
            content_type=ContentType.ARTICLE,
            external_id=f"art-{uuid.uuid4().hex[:6]}",
            canonical_url=f"https://tech.com/optics-{uuid.uuid4().hex[:5]}",
            content_hash=uuid.uuid4().hex,
            title="Optics Lab Claims 10x Bandwidth Leap",
            summary_raw="Independent verification confirms optical photonic interconnect benchmarks.",
            tags=["photonic", "optics"],
            published_at=now,
            processing_status=ProcessingStatus.PROCESSED,
        )
        session.add(doc)
        await session.commit()

        timeline_data = await get_story_timeline(doc.id, session)
        await session.commit()
        assert timeline_data["total_events"] >= 1
        assert "consensus_status" in timeline_data
        assert "timeline" in timeline_data

        # Test API endpoint
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            res = await ac.get(f"/api/v1/trends/documents/{doc.id}/timeline")
            assert res.status_code == 200
            data = res.json()
            assert data["document_id"] == str(doc.id)
            assert len(data["timeline"]) >= 1


@pytest.mark.asyncio
async def test_watchlists_and_notifications_rls(test_session_factory):
    """Test watchlist creation with vector embedding, document matching, and notifications."""
    async with test_session_factory() as session:
        # Create test user
        user = User(
            id=uuid.uuid4(),
            email=f"tester-{uuid.uuid4().hex[:6]}@devaintelligence.local",
            full_name="Trend Tester",
            role=UserRole.USER,
        )
        session.add(user)
        await session.commit()

        token = create_access_token(subject=str(user.id), role=user.role.value)
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            # 1. Create a watchlist
            create_payload = {
                "name": "Quantum PINNs Radar",
                "query_text": "Physics-informed neural networks with quantum acceleration",
                "min_similarity": 0.50,
                "is_active": True,
            }
            res = await ac.post("/api/v1/users/me/watchlists", json=create_payload, headers=headers)
            assert res.status_code == 201
            wl = res.json()
            watchlist_id = wl["id"]
            assert wl["name"] == "Quantum PINNs Radar"

            # 2. List watchlists
            res_list = await ac.get("/api/v1/users/me/watchlists", headers=headers)
            assert res_list.status_code == 200
            assert len(res_list.json()) >= 1

            # 3. Trigger document matching
            wl_obj = await session.get(SemanticWatchlist, uuid.UUID(watchlist_id))
            assert wl_obj.query_embedding is not None

            # Create a matching test document
            source = Source(
                id=uuid.uuid4(),
                name=f"Watchlist Test Source {uuid.uuid4().hex[:6]}",
                slug=f"wl-source-{uuid.uuid4().hex[:6]}",
                category=SourceCategory.RESEARCH,
                adapter_key="arxiv",
                base_url="https://arxiv.org",
                config={},
            )
            session.add(source)
            await session.flush()

            doc = Document(
                id=uuid.uuid4(),
                source_id=source.id,
                content_type=ContentType.PAPER,
                external_id=f"wl-doc-{uuid.uuid4().hex[:6]}",
                canonical_url=f"https://arxiv.org/abs/2602.{uuid.uuid4().hex[:5]}",
                content_hash=uuid.uuid4().hex,
                title="Accelerated Quantum Physics-Informed Neural Networks",
                summary_raw="Solving Navier-Stokes equations via quantum tensor networks and PINNs.",
                tags=["quantum", "pinns"],
                published_at=datetime.now(timezone.utc),
                processing_status=ProcessingStatus.PROCESSED,
            )
            session.add(doc)
            await session.flush()

            matched = await PersonalizationEngine.match_document_to_watchlists(
                document=doc,
                doc_embedding=wl_obj.query_embedding,
                db=session,
            )
            await session.commit()
            assert len(matched) >= 1

            # 4. Check notification endpoint
            notif_res = await ac.get("/api/v1/users/me/notifications", headers=headers)
            assert notif_res.status_code == 200
            notifs = notif_res.json()
            assert len(notifs) >= 1
            notif_id = notifs[0]["id"]
            assert "Watchlist Alert" in notifs[0]["title"]

            # 5. Mark notification read
            read_res = await ac.patch(f"/api/v1/users/me/notifications/{notif_id}/read", headers=headers)
            assert read_res.status_code == 200
            assert read_res.json()["is_read"] is True

            # 6. Delete watchlist
            del_res = await ac.delete(f"/api/v1/users/me/watchlists/{watchlist_id}", headers=headers)
            assert del_res.status_code == 204
