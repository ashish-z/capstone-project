"""Tests for Pydantic validation at the tool boundary."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from freight_copilot.tools.carrier_history import carrier_history
from freight_copilot.tools.external_events import external_events
from freight_copilot.tools.models import (
    LaneHistory,
    PortEvents,
    ShipmentRecord,
)
from freight_copilot.tools.shipment_lookup import lookup_shipment


def test_lookup_returns_validated_shipment_record() -> None:
    raw = lookup_shipment.invoke({"shipment_id": "FRT-1042"})
    parsed = json.loads(raw)
    # Round-trip through the model — proves the tool's output matches the contract.
    record = ShipmentRecord.model_validate(parsed)
    assert record.shipment_id == "FRT-1042"
    assert record.carrier == "Maersk"
    assert record.customer.tier == "Gold"


def test_carrier_history_returns_validated_lane_history() -> None:
    raw = carrier_history.invoke({"lane": "INNSA-USNYC"})
    parsed = json.loads(raw)
    history = LaneHistory.model_validate(parsed)
    assert history.lane == "INNSA-USNYC"
    assert len(history.carriers) >= 2
    for c in history.carriers:
        assert c.on_time_pct >= 0
        assert c.shipments >= 0


def test_external_events_returns_validated_port_events() -> None:
    raw = external_events.invoke({"port_code": "USHOU"})
    parsed = json.loads(raw)
    events = PortEvents.model_validate(parsed)
    assert events.port_code == "USHOU"
    assert events.events  # has at least one (the storm)
    assert events.events[0].type == "weather"


def test_malformed_payload_raises_at_boundary() -> None:
    """Sanity: feeding ShipmentRecord garbage fails fast, not silently."""
    with pytest.raises(ValidationError):
        ShipmentRecord.model_validate({"shipment_id": "x"})  # missing required fields


def test_unknown_shipment_returns_typed_error() -> None:
    raw = lookup_shipment.invoke({"shipment_id": "FRT-9999"})
    payload = json.loads(raw)
    assert payload["error"] == "shipment_not_found"
    assert payload["shipment_id"] == "FRT-9999"
