import time
import uuid
import os
import pytest

# Ensure test mode is active for fast deterministic in-memory vector embeddings
os.environ["TESTING"] = "True"
os.environ["ENVIRONMENT"] = "test"

from app.modules.retrieval.query_expander import expand_technical_query
from app.modules.retrieval.reranker import (
    reciprocal_rank_fusion,
    FusedChunkCandidate,
)
from app.modules.retrieval.retriever import ChunkCandidate
from app.modules.retrieval.service import HybridRetrievalService, SearchRequest
from app.db.session import async_session_factory


def test_technical_acronym_expansion():
    """Verify bidirectional expansion for PINNs, FNO, vLLM, and RLHF."""
    t0 = time.perf_counter()
    res_pinn = expand_technical_query("PINNs")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 5.0, f"Query expansion took {elapsed_ms}ms, expected < 5ms"
    assert "physics-informed neural networks" in res_pinn["expanded_terms"]
    assert "partial differential equations" in res_pinn["expanded_terms"]
    assert "physics-informed neural networks" in res_pinn["semantic_query"]

    # FNO
    res_fno = expand_technical_query("fno")
    assert "fourier neural operator" in res_fno["expanded_terms"]

    # vLLM
    res_vllm = expand_technical_query("vllm")
    assert "pagedattention" in res_vllm["expanded_terms"]
    assert "kv cache" in res_vllm["expanded_terms"]

    # RLHF / DPO
    res_dpo = expand_technical_query("dpo")
    assert "preference optimization" in res_dpo["expanded_terms"]


def test_rrf_domain_authority_and_exact_boost():
    """Verify exact match boost (+0.008) and verified code boost (+0.004) in RRF."""
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()

    chunk_a = ChunkCandidate(
        chunk_id=uuid.uuid4(),
        document_id=doc_a,
        chunk_index=0,
        section_type="abstract",
        content="Physics-informed neural networks for solving partial differential equations.",
        token_count=50,
        lexical_rank=2,
        vector_rank=2,
    )

    chunk_b = ChunkCandidate(
        chunk_id=uuid.uuid4(),
        document_id=doc_b,
        chunk_index=0,
        section_type="abstract",
        content="General neural network architecture for generic classification tasks.",
        token_count=50,
        lexical_rank=1,
        vector_rank=1,
    )

    doc_meta = {
        doc_a: {
            "title": "PINNs: Physics-Informed Neural Networks",
            "tags": ["pinn", "cs.ai"],
            "has_code_link": True,
        },
        doc_b: {
            "title": "A Generic Neural Network Classifier",
            "tags": ["cs.lg"],
            "has_code_link": False,
        },
    }

    fused = reciprocal_rank_fusion(
        lexical_candidates=[chunk_b, chunk_a],
        vector_candidates=[chunk_b, chunk_a],
        k=60,
        doc_metadata_map=doc_meta,
        query_terms=["pinn", "physics-informed neural networks"],
    )

    # doc_a gets +0.008 (exact title/tag match) + 0.004 (code link) = +0.012
    # Even though doc_b was rank 1 in lexical & vector (score ~0.03278), doc_a (score ~0.03225 + 0.012 = 0.04425) overtakes it!
    assert fused[0].document_id == doc_a
    assert "pinn" in fused[0].matched_terms


@pytest.mark.asyncio
async def test_chunk_deduplication_and_latency():
    """Verify max 2 chunks per document, score normalization, and cached response."""
    async with async_session_factory() as session:
        service = HybridRetrievalService(session)

        req = SearchRequest(
            query="neural network",
            top_k=8,
            mode="hybrid",
        )

        res = await service.search(req)

        assert "results" in res
        assert "latency_ms" in res
        assert "expanded_terms" in res

        # Verify chunk deduplication: at most 2 chunks per document
        doc_counts = {}
        for r in res["results"]:
            did = r["document_id"]
            doc_counts[did] = doc_counts.get(did, 0) + 1
            assert doc_counts[did] <= 2, f"Document {did} returned > 2 chunks!"
            assert "relevance_score" in r
            assert 0.0 <= r["relevance_score"] <= 1.0

        # Verify second hit leverages Redis / caching layer for sub-50ms response
        cached_res = await service.search(req)
        assert cached_res["cache_hit"] is True
        assert cached_res["latency_ms"] < 50.0
