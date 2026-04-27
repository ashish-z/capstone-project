"""Tests for the recall_customer_history and recall_shipment_history tools.

These tests use the seeded production memory db (data/memory.sqlite3).
They will fail if the db hasn't been seeded — run:
    PYTHONPATH=src python -m freight_copilot.memory.seed
"""

from __future__ import annotations

import json

import pytest

from freight_copilot.memory.store import _db_path
from freight_copilot.tools.recall import (
    recall_customer_history,
    recall_shipment_history,
)


pytestmark = pytest.mark.skipif(
    not _db_path().exists(),
    reason="memory db not seeded — run `python -m freight_copilot.memory.seed`",
)


def test_recall_customer_returns_seeded_notes() -> None:
    raw = recall_customer_history.invoke({"customer_name": "Brookline Apparel Co"})
    payload = json.loads(raw)
    assert payload["customer_name"] == "Brookline Apparel Co"
    assert len(payload["notes"]) >= 1
    # At least one of the seeded notes mentions the shipper response time.
    assert any("Aurora" in n["note"] or "shipper" in n["note"].lower() for n in payload["notes"])


def test_recall_customer_surfaces_corrections() -> None:
    raw = recall_customer_history.invoke({"customer_name": "Brookline Apparel Co"})
    payload = json.loads(raw)
    assert len(payload["corrections"]) >= 1
    assert any("procurement@" in c["correction"] for c in payload["corrections"])


def test_recall_shipment_returns_seeded_notes() -> None:
    raw = recall_shipment_history.invoke({"shipment_id": "FRT-1042"})
    payload = json.loads(raw)
    assert payload["shipment_id"] == "FRT-1042"
    assert len(payload["notes"]) >= 1


def test_recall_unknown_entity_returns_empty_arrays() -> None:
    raw = recall_customer_history.invoke({"customer_name": "Nonexistent Co Ltd"})
    payload = json.loads(raw)
    assert payload["notes"] == []
    assert payload["corrections"] == []
