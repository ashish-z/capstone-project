"""Tests for the external_events tool."""

from __future__ import annotations

import json

from freight_copilot.tools.external_events import external_events


def test_port_with_active_event_returns_event() -> None:
    raw = external_events.invoke({"port_code": "USHOU"})
    payload = json.loads(raw)
    assert payload["port_code"] == "USHOU"
    assert len(payload["events"]) >= 1
    event = payload["events"][0]
    assert event["type"] == "weather"
    assert "summary" in event
    assert "source" in event


def test_quiet_port_returns_empty_events_list() -> None:
    raw = external_events.invoke({"port_code": "INNSA"})
    payload = json.loads(raw)
    assert payload["port_code"] == "INNSA"
    assert payload["events"] == []


def test_uncovered_port_returns_error() -> None:
    raw = external_events.invoke({"port_code": "ZZZZZ"})
    payload = json.loads(raw)
    assert payload["error"] == "port_not_covered"
    assert payload["port_code"] == "ZZZZZ"
