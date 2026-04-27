"""SOP retrieval tool — semantic search over the SOP knowledge base."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from freight_copilot.retrieval.store import search

_DEFAULT_K = 4
_MAX_K = 8


@tool
def search_sops(query: str, k: int = _DEFAULT_K) -> str:
    """Search the freight ops SOP knowledge base for procedural guidance.

    Use this tool whenever you need policy or procedural guidance beyond raw
    shipment data — e.g., "what's our escalation matrix for a Gold tier
    customer?", "how do we handle a missing Commercial Invoice?", "what's
    the customer-comm SLA for Platinum?".

    Returns the top-k most semantically relevant SOP chunks. Each chunk
    includes the source filename so you can cite it in your reasoning
    (e.g., "per sop-customs-hold-missing-ci.md"). Distance is cosine —
    lower means closer match.

    Args:
        query: Natural-language search query.
        k: Number of chunks to return (default 4, max 8).

    Returns:
        JSON string with a list of result objects: {source, chunk_index,
        section, distance, text}.
    """
    k = max(1, min(k, _MAX_K))
    results = search(query, k=k)
    return json.dumps(
        {"query": query, "k": k, "results": results},
        ensure_ascii=False,
        indent=2,
    )
