import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pydantic import BaseModel, Field
from app.core.llm_provider import MockLLMProvider, get_llm_provider
from app.core.embeddings import EmbeddingService
from app.workers.system_tasks import ping_worker


class NestedAuthor(BaseModel):
    name: str = Field(..., description="Author's full name")
    affiliation: str = Field(..., description="Institution or lab")


class ResearchIntelligenceSpec(BaseModel):
    title: str = Field(..., description="Paper or technology title")
    stars: int = Field(..., description="Popularity metric")
    relevance_score: float = Field(..., description="Calculated relevance")
    is_breakthrough: bool = Field(..., description="Flag indicating novelty")
    tags: list[str] = Field(..., description="Keyword tags")
    author: NestedAuthor = Field(..., description="Lead author metadata")


@pytest.mark.asyncio
async def test_health_live_endpoint(client):
    """Exit Gate 1: GET /api/v1/health/live returns 200 with valid status and version."""
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_ready_endpoint_mocked(client):
    """Exit Gate 2: GET /api/v1/health/ready checks Postgres, pgvector extension, Redis, and Celery."""
    # Mock Postgres connection via AsyncMock
    mock_conn = AsyncMock()
    mock_ext_res = MagicMock()
    mock_ext_res.scalar_one_or_none.return_value = "vector"

    async def fake_execute(stmt):
        stmt_str = str(stmt)
        if "pg_extension" in stmt_str:
            return mock_ext_res
        return MagicMock()

    mock_conn.execute.side_effect = fake_execute

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value.__aexit__.return_value = None

    with patch("app.api.v1.health.engine", mock_engine):
        # Mock Redis ping
        with patch("redis.asyncio.from_url") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.aclose = AsyncMock(return_value=None)
            mock_redis_cls.return_value = mock_redis

            # Mock Celery ping inspect
            with patch("app.api.v1.health.celery_app.control.inspect") as mock_inspect:
                inspect_instance = MagicMock()
                inspect_instance.ping.return_value = {"celery@worker-node-1": {"ok": "pong"}}
                mock_inspect.return_value = inspect_instance

                response = await client.get("/api/v1/health/ready")
                print("DEBUG HEALTH READY RESPONSE:", response.status_code, response.json())
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert "components" in data
                assert data["components"]["postgres"]["status"] == "healthy"
                assert data["components"]["postgres"]["pgvector"] is True
                assert data["components"]["redis"]["status"] == "healthy"
                assert data["components"]["celery"]["status"] == "healthy"
                assert "celery@worker-node-1" in data["components"]["celery"]["workers"]


@pytest.mark.asyncio
async def test_mock_llm_provider_structured_output():
    """Exit Gate 3: MockLLMProvider accurately instantiates and validates a nested Pydantic schema."""
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)

    messages = [{"role": "user", "content": "Analyze the latest transformer architecture paper."}]
    result = await provider.generate_structured(messages=messages, schema=ResearchIntelligenceSpec)

    assert isinstance(result, ResearchIntelligenceSpec)
    assert isinstance(result.title, str)
    assert isinstance(result.stars, int)
    assert isinstance(result.relevance_score, float)
    assert isinstance(result.is_breakthrough, bool)
    assert isinstance(result.tags, list)
    assert len(result.tags) > 0
    assert isinstance(result.author, NestedAuthor)
    assert isinstance(result.author.name, str)
    assert isinstance(result.author.affiliation, str)


def test_embedding_service_test_mode():
    """Exit Gate 4: EmbeddingService returns 768-dimensional normalized vectors and cross-encoder scores cleanly."""
    embed_service = EmbeddingService()

    # Query embedding
    query_vec = embed_service.embed_query("Graph Neural Networks for Drug Discovery")
    assert len(query_vec) == 768
    assert isinstance(query_vec[0], float)

    # Document embeddings
    docs = [
        "Knowledge graphs representation learning",
        "Deep learning advances in NLP",
        "Autonomous code generation benchmarks",
    ]
    doc_vecs = embed_service.embed_documents(docs)
    assert len(doc_vecs) == 3
    for vec in doc_vecs:
        assert len(vec) == 768

    # Reranking
    reranked = embed_service.rerank("knowledge graphs", docs)
    assert len(reranked) == 3
    assert reranked[0]["score"] >= reranked[1]["score"]
    assert "score" in reranked[0]
    assert "document" in reranked[0]


def test_system_ping_worker_task():
    """Exit Gate 5: system.ping_worker task executes and returns expected diagnostic payload."""
    res = ping_worker.apply()
    result = res.result
    assert result["status"] == "pong"
    assert "timestamp" in result
    assert "worker" in result
    assert "active and accepting tasks" in result["message"]
