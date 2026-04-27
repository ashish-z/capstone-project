"""Tests for the long-term memory SQLite store.

Tests run against a temporary SQLite db (MEMORY_DB env var) so they don't
clobber the seeded production db.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def memory_db(monkeypatch: pytest.MonkeyPatch):
    """Point the store at a fresh temp db for the duration of the test."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test-memory.sqlite3"
        monkeypatch.setenv("MEMORY_DB", str(db_path))
        # Force a fresh import so the path is read off the env var.
        import importlib

        from freight_copilot.memory import store

        importlib.reload(store)
        store.init_db()
        yield store
        # Cleanup happens via the tempdir context manager.


def test_add_and_list_customer_note(memory_db) -> None:
    s = memory_db
    rec_id = s.add_customer_note(
        s.CustomerNote(
            ts=s.now(),
            customer_name="Test Co",
            note="Test note",
            source_thread_id="t-1",
        )
    )
    assert rec_id > 0
    notes = s.list_customer_notes("Test Co")
    assert len(notes) == 1
    assert notes[0].note == "Test note"


def test_add_and_list_shipment_note(memory_db) -> None:
    s = memory_db
    s.add_shipment_note(
        s.ShipmentNote(
            ts=s.now(),
            shipment_id="FRT-9999",
            note="Triaged the test shipment",
            source_thread_id="t-1",
        )
    )
    notes = s.list_shipment_notes("FRT-9999")
    assert len(notes) == 1
    assert "Triaged" in notes[0].note


def test_corrections_are_filtered_by_entity(memory_db) -> None:
    s = memory_db
    s.add_correction(
        s.Correction(
            ts=s.now(),
            entity_kind="customer",
            entity_id="ACME Inc.",
            correction="Customer is Gold, not Silver",
            source_thread_id="t-1",
        )
    )
    s.add_correction(
        s.Correction(
            ts=s.now(),
            entity_kind="shipment",
            entity_id="FRT-1042",
            correction="ETA is 2026-04-29, not 2026-04-30",
            source_thread_id="t-1",
        )
    )

    cust = s.list_corrections("customer", "ACME Inc.")
    assert len(cust) == 1
    assert "Gold" in cust[0].correction

    ship = s.list_corrections("shipment", "FRT-1042")
    assert len(ship) == 1
    assert "ETA" in ship[0].correction


def test_list_orders_by_recency_desc(memory_db) -> None:
    s = memory_db
    base = s.now()
    s.add_customer_note(
        s.CustomerNote(ts=base, customer_name="X", note="older")
    )
    s.add_customer_note(
        s.CustomerNote(ts=base + 100, customer_name="X", note="newer")
    )
    notes = s.list_customer_notes("X")
    assert notes[0].note == "newer"
    assert notes[1].note == "older"


def test_reset_clears_all(memory_db) -> None:
    s = memory_db
    s.add_customer_note(s.CustomerNote(ts=s.now(), customer_name="X", note="n"))
    assert len(s.list_customer_notes("X")) == 1
    s.reset_db()
    assert len(s.list_customer_notes("X")) == 0
