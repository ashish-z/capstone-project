"""Tests for the lookup_shipment tool."""

from __future__ import annotations

import json

import pytest

from freight_copilot.tools.shipment_lookup import lookup_shipment


@pytest.mark.parametrize(
    "shipment_id,expected_status",
    [
        ("FRT-1042", "HELD - Customs"),
        ("FRT-1043", "DELAYED - External Event"),
        ("FRT-1044", "ROLLED"),
        ("FRT-1045", "ETA SLIPPED - No Update"),
        ("FRT-1046", "HELD - Doc Discrepancy"),
    ],
)
def test_lookup_returns_correct_record(shipment_id: str, expected_status: str) -> None:
    raw = lookup_shipment.invoke({"shipment_id": shipment_id})
    record = json.loads(raw)
    assert record["shipment_id"] == shipment_id
    assert record["current_status"] == expected_status


def test_lookup_returns_full_payload_shape() -> None:
    raw = lookup_shipment.invoke({"shipment_id": "FRT-1042"})
    record = json.loads(raw)
    # Spot-check the contract: critical fields the agent will rely on.
    for key in (
        "shipment_id",
        "carrier",
        "vessel",
        "etd",
        "eta",
        "current_status",
        "exception_summary",
        "tracking_events",
        "documents",
    ):
        assert key in record, f"missing field: {key}"
    assert isinstance(record["tracking_events"], list)
    assert len(record["tracking_events"]) > 0


def test_lookup_unknown_shipment_returns_error_payload() -> None:
    raw = lookup_shipment.invoke({"shipment_id": "FRT-9999"})
    record = json.loads(raw)
    assert record.get("error") == "shipment_not_found"
    assert record["shipment_id"] == "FRT-9999"
