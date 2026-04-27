"""Tests for the SOP retrieval layer.

These tests assume the SOP corpus has already been ingested into Chroma.
If you ever blow away chroma_db/, re-run:
    PYTHONPATH=src python -m freight_copilot.retrieval.ingest
"""

from __future__ import annotations

import json

import pytest

from freight_copilot.retrieval.store import get_collection, search
from freight_copilot.tools.search_sops import search_sops


def test_collection_has_chunks() -> None:
    coll = get_collection()
    # We ingest 9 SOPs; chunking yields ~70+ chunks total.
    assert coll.count() >= 50, f"too few chunks ingested: {coll.count()}"


@pytest.mark.parametrize(
    "query,expected_source",
    [
        ("missing commercial invoice customs hold", "sop-customs-hold-missing-ci.md"),
        ("port closed weather storm", "sop-weather-port-closure.md"),
        ("vessel rolled overbooking", "sop-capacity-rollover.md"),
        ("ETA slipped no carrier update silent", "sop-silent-eta-slippage.md"),
        ("HBL MBL consignee mismatch entity suffix", "sop-doc-discrepancy-hbl-mbl.md"),
        ("demurrage waiver request goodwill", "sop-demurrage-management.md"),
        ("escalation thresholds senior ops handoff", "sop-escalation-handoff.md"),
    ],
)
def test_canonical_query_retrieves_right_sop_in_topk(
    query: str, expected_source: str
) -> None:
    """The matching SOP must appear in the top-4 results.

    We assert top-4 rather than top-1 because the agent reads k=4 chunks by
    default — being #2 with a relevant chunk is functionally equivalent to
    being #1 for the agent's purposes.
    """
    results = search(query, k=4)
    assert results, f"empty results for query: {query}"
    sources = [r["source"] for r in results]
    assert expected_source in sources, (
        f"'{expected_source}' missing from top-4 for query '{query}'. "
        f"Got: {[(r['source'], round(r['distance'], 3)) for r in results]}"
    )


def test_search_sops_tool_returns_valid_json_with_citations() -> None:
    raw = search_sops.invoke(
        {"query": "Gold tier customer SLA acknowledgment window", "k": 3}
    )
    payload = json.loads(raw)
    assert "results" in payload
    assert len(payload["results"]) <= 3
    for r in payload["results"]:
        # Every result must have what the agent needs to cite it.
        assert "source" in r
        assert r["source"].startswith("sop-")
        assert r["source"].endswith(".md")
        assert "text" in r
        assert "distance" in r


def test_search_sops_clamps_k_to_max() -> None:
    raw = search_sops.invoke({"query": "anything", "k": 99})
    payload = json.loads(raw)
    assert payload["k"] == 8  # _MAX_K
    assert len(payload["results"]) <= 8
