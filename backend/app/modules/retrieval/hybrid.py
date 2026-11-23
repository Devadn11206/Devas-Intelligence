"""Hybrid retrieval compatibility module.

Provides direct access to HybridRetrievalService, Query Expander, and RRF re-rankers.
"""

from app.modules.retrieval.service import RetrievalService, HybridRetrievalService
from app.modules.retrieval.query_expander import expand_technical_query
from app.modules.retrieval.query_parser import SearchRequest
from app.modules.retrieval.reranker import reciprocal_rank_fusion, cross_encoder_rerank

__all__ = [
    "HybridRetrievalService",
    "RetrievalService",
    "expand_technical_query",
    "SearchRequest",
    "reciprocal_rank_fusion",
    "cross_encoder_rerank",
]
