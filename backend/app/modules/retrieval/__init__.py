"""Hybrid Retrieval Domain Package.

Exposes HybridRetrievalService, Query Expander, and Dual-Path components.
"""

from app.modules.retrieval.service import RetrievalService, HybridRetrievalService
from app.modules.retrieval.query_expander import expand_technical_query
from app.modules.retrieval.query_parser import SearchRequest
from app.modules.retrieval.retriever import DualPathRetriever, ChunkCandidate
from app.modules.retrieval.reranker import (
    FusedChunkCandidate,
    reciprocal_rank_fusion,
    cross_encoder_rerank,
)

__all__ = [
    "RetrievalService",
    "HybridRetrievalService",
    "expand_technical_query",
    "SearchRequest",
    "DualPathRetriever",
    "ChunkCandidate",
    "FusedChunkCandidate",
    "reciprocal_rank_fusion",
    "cross_encoder_rerank",
]
