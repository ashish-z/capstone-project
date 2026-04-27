"""SOP ingest — chunks all .md files in data/sops/ and writes to Chroma.

Run as:  python -m freight_copilot.retrieval.ingest
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from freight_copilot.retrieval.store import reset_collection

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SOP_DIR = _REPO_ROOT / "data" / "sops"

# Tuned for SOP markdown — sections are short, so smaller chunks with
# generous overlap give the retriever multiple shots at the right context.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def _section_for_chunk(chunk: str, source_text: str) -> str:
    """Best-effort: which markdown ## heading does this chunk live under?

    Walks back from the chunk's start position in the source, finds the
    most recent `## Heading`, and returns the heading text. Falls back to
    the document's H1 title if no ## found.
    """
    # Find chunk start in source
    idx = source_text.find(chunk[:80])  # use prefix to handle splitter trimming
    if idx < 0:
        return ""
    prior = source_text[:idx]
    h2_matches = list(re.finditer(r"^##\s+(.+?)$", prior, flags=re.MULTILINE))
    if h2_matches:
        return h2_matches[-1].group(1).strip()
    h1 = re.search(r"^#\s+(.+?)$", source_text, flags=re.MULTILINE)
    return h1.group(1).strip() if h1 else ""


def ingest() -> dict:
    """Re-ingest all SOPs into a fresh collection. Returns ingest stats."""
    sop_files = sorted(_SOP_DIR.glob("*.md"))
    if not sop_files:
        raise FileNotFoundError(f"No SOPs found in {_SOP_DIR}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    coll = reset_collection()

    docs: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []

    per_file: dict[str, int] = {}
    for sop_path in sop_files:
        text = sop_path.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)
        per_file[sop_path.name] = len(chunks)
        for i, chunk in enumerate(chunks):
            docs.append(chunk)
            metas.append(
                {
                    "source": sop_path.name,
                    "chunk_index": i,
                    "section": _section_for_chunk(chunk, text),
                }
            )
            ids.append(f"{sop_path.stem}-{i}")

    # Chroma's add() embeds in one batch (sentence-transformers handles
    # batching internally; ~50 chunks is trivial).
    coll.add(documents=docs, metadatas=metas, ids=ids)

    return {
        "total_chunks": len(docs),
        "files": per_file,
        "collection_name": coll.name,
    }


if __name__ == "__main__":
    import json

    stats = ingest()
    print(json.dumps(stats, indent=2))
