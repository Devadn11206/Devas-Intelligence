import math
from typing import Any, List
from app.core.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self._embedder: Any = None
        self._reranker: Any = None
        self._device: str | None = None

    @property
    def device(self) -> str:
        if self._device is None:
            try:
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self._device = "cpu"
        return self._device

    def _is_testing(self) -> bool:
        import os
        settings = get_settings()
        return settings.TESTING or os.environ.get("TESTING") == "True" or os.environ.get("ENVIRONMENT") == "test"

    def _get_embedder(self) -> Any:
        if self._is_testing():
            return None
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(get_settings().EMBEDDING_MODEL, device=self.device)
        return self._embedder

    def _get_reranker(self) -> Any:
        if self._is_testing():
            return None
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(get_settings().RERANKER_MODEL, device=self.device)
        return self._reranker

    def _get_deterministic_mock_vector(self, text: str, dim: int = 768) -> List[float]:
        # Generate stable, zero-centered pseudo-random unit vector using MD5 hash seed
        import hashlib
        import random
        # Seed python random with md5 of text so identical texts get identical vectors,
        # but different texts get approximately orthogonal random vectors (cosine sim ~ 0)
        seed_int = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed_int)
        raw = [rng.gauss(0.0, 1.0) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [round(x / norm, 6) for x in raw]

    def embed_query(self, query: str) -> List[float]:
        if self._is_testing():
            return self._get_deterministic_mock_vector(query, get_settings().EMBEDDING_DIM)

        embedder = self._get_embedder()
        vector = embedder.encode(query, normalize_embeddings=True)
        return vector.tolist()

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        if self._is_testing():
            return [self._get_deterministic_mock_vector(doc, get_settings().EMBEDDING_DIM) for doc in documents]

        embedder = self._get_embedder()
        vectors = embedder.encode(documents, normalize_embeddings=True)
        return vectors.tolist()

    def rerank(self, query: str, documents: List[str]) -> List[dict[str, Any]]:
        if self._is_testing() or not documents:
            # Deterministic scoring for test mode based on lexical overlap + rank
            results = []
            q_words = set(query.lower().split())
            for idx, doc in enumerate(documents):
                doc_words = set(doc.lower().split())
                overlap = len(q_words.intersection(doc_words))
                score = round(overlap * 1.0 + (1.0 / (idx + 1)), 4)
                results.append({"index": idx, "document": doc, "score": score})
            return sorted(results, key=lambda x: x["score"], reverse=True)

        reranker = self._get_reranker()
        pairs = [[query, doc] for doc in documents]
        scores = reranker.predict(pairs)
        results = [
            {"index": idx, "document": doc, "score": float(score)}
            for idx, (doc, score) in enumerate(zip(documents, scores))
        ]
        return sorted(results, key=lambda x: x["score"], reverse=True)


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
