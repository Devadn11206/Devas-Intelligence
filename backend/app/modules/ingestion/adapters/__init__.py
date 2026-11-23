"""Ingestion adapter registrations."""
from app.modules.ingestion.base import AdapterRegistry
from app.modules.ingestion.adapters.arxiv import ArxivAdapter
from app.modules.ingestion.adapters.github import GitHubAdapter
from app.modules.ingestion.adapters.huggingface import HuggingFaceAdapter
from app.modules.ingestion.adapters.semantic_scholar import SemanticScholarAdapter
from app.modules.ingestion.adapters.rss import RSSAdapter

# Register all 5 adapters
AdapterRegistry.register("arxiv", ArxivAdapter)
AdapterRegistry.register("github", GitHubAdapter)
AdapterRegistry.register("huggingface", HuggingFaceAdapter)
AdapterRegistry.register("semantic_scholar", SemanticScholarAdapter)
AdapterRegistry.register("rss", RSSAdapter)

__all__ = [
    "AdapterRegistry",
    "ArxivAdapter",
    "GitHubAdapter",
    "HuggingFaceAdapter",
    "SemanticScholarAdapter",
    "RSSAdapter",
]
