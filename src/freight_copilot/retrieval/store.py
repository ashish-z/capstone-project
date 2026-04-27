"""ChromaDB-backed vector store for the SOP corpus.

We use Chroma's PersistentClient with the sentence-transformers embedding
function (all-MiniLM-L6-v2 — 384-dim, runs locally on CPU, free).
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

_REPO_ROOT = Path(__file__).resolve().parents[3]

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", str(_REPO_ROOT / "chroma_db"))
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
COLLECTION_NAME = "freight_sops"

# sentence-transformers/all-MiniLM-L6-v2 → strip the namespace for chroma's
# downloader, which expects the bare model name.
_EMBED_MODEL_NAME = EMBED_MODEL.split("/")[-1]


def _client() -> chromadb.api.ClientAPI:
    return chromadb.PersistentClient(path=CHROMA_DIR)


def _embed_fn() -> embedding_functions.EmbeddingFunction:
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=_EMBED_MODEL_NAME
    )


def get_collection() -> Collection:
    """Return the SOP collection, creating it if missing."""
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embed_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection() -> Collection:
    """Drop and recreate the collection (used by ingest for idempotency)."""
    client = _client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001 — ok if it doesn't exist
        pass
    return client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embed_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def search(query: str, k: int = 4) -> list[dict]:
    """Return top-k matching chunks with source metadata and cosine distance."""
    coll = get_collection()
    res = coll.query(query_texts=[query], n_results=k)
    docs = res["documents"][0] if res["documents"] else []
    metas = res["metadatas"][0] if res["metadatas"] else []
    dists = res["distances"][0] if res["distances"] else []
    return [
        {
            "source": meta.get("source", "unknown"),
            "chunk_index": meta.get("chunk_index", -1),
            "section": meta.get("section", ""),
            "distance": dist,
            "text": doc,
        }
        for doc, meta, dist in zip(docs, metas, dists, strict=False)
    ]
