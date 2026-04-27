"""Tests for the carrier_history tool."""

from __future__ import annotations

import json

from freight_copilot.tools.carrier_history import carrier_history


def test_known_lane_returns_carriers() -> None:
    raw = carrier_history.invoke({"lane": "INNSA-USNYC"})
    payload = json.loads(raw)
    assert payload["lane"] == "INNSA-USNYC"
    assert isinstance(payload["carriers"], list)
    assert len(payload["carriers"]) >= 2
    # Each carrier record has the contract fields the agent reads.
    for c in payload["carriers"]:
        assert "carrier" in c
        assert "on_time_pct" in c
        assert "shipments" in c


def test_unknown_lane_returns_error_with_lane_list() -> None:
    raw = carrier_history.invoke({"lane": "XXNON-XXEXIST"})
    payload = json.loads(raw)
    assert payload["error"] == "lane_not_found"
    assert payload["lane"] == "XXNON-XXEXIST"
    # The error path lists available lanes so the agent can self-correct.
    assert "lanes_available" in payload
    assert len(payload["lanes_available"]) > 0


def test_all_at_fixture_lanes_have_history() -> None:
    """Every shipment fixture's lane must exist in lane_history (eval invariant)."""
    expected_lanes = [
        "INNSA-USNYC",  # FRT-1042
        "CNNGB-USHOU",  # FRT-1043
        "VNSGN-DEHAM",  # FRT-1044
        "SGSIN-AUMEL",  # FRT-1045
        "CNSHA-GBFXT",  # FRT-1046
    ]
    for lane in expected_lanes:
        raw = carrier_history.invoke({"lane": lane})
        payload = json.loads(raw)
        assert "error" not in payload, f"missing history for lane {lane}"
        assert len(payload["carriers"]) > 0
