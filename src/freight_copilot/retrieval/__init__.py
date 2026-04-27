"""RAG / retrieval layer — Chroma + sentence-transformers."""

from freight_copilot.retrieval.store import get_collection, search

__all__ = ["get_collection", "search"]
