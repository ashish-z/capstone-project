"""Tests for the monitoring aggregations.

We don't read the live logs/ directory in tests — we feed the aggregator
synthetic turn dicts so behavior is deterministic.
"""

from __future__ import annotations

import time

import pytest

from freight_copilot.monitoring import (
    Alert,
    AlertThresholds,
    Metrics,
    aggregate_metrics,
    derive_alerts,
)


def _turn(**overrides) -> dict:
    base = {
        "ts": time.time(),
        "thread_id": "t1",
        "turn_index": 1,
        "user_input": "Triage FRT-1042",
        "tool_calls": [],
        "final_response": "ok",
        "total_duration_ms": 1000,
        "input_tokens": 1000,
        "output_tokens": 500,
        "model": "claude-haiku-4-5",
        "intent": "triage_request",
        "intent_confidence": 0.9,
        "persona": "ops_associate",
        "safety_findings": [],
        "error": None,
    }
    base.update(overrides)
    return base


def test_empty_input_returns_zero_metrics() -> None:
    m = aggregate_metrics([])
    assert m == Metrics()


def test_basic_counts_and_distinct_sessions() -> None:
    turns = [
        _turn(thread_id="A"),
        _turn(thread_id="A", turn_index=2),
        _turn(thread_id="B"),
    ]
    m = aggregate_metrics(turns)
    assert m.n_turns == 3
    assert m.n_sessions == 2


def test_latency_percentiles() -> None:
    turns = [_turn(total_duration_ms=ms) for ms in (100, 200, 300, 400, 9_000)]
    m = aggregate_metrics(turns)
    assert m.latency_ms_p50 == pytest.approx(300, abs=1)
    assert m.latency_ms_p95 == pytest.approx(9_000, abs=1)
    assert m.latency_ms_avg == pytest.approx(2_000, abs=1)


def test_token_and_cost_aggregation() -> None:
    turns = [
        _turn(input_tokens=1_000_000, output_tokens=200_000),
        _turn(input_tokens=500_000, output_tokens=100_000),
    ]
    m = aggregate_metrics(turns, price_per_mtok=(1.0, 5.0))
    assert m.total_input_tokens == 1_500_000
    assert m.total_output_tokens == 300_000
    # 1.5 MTok in @ $1 + 0.3 MTok out @ $5 = $3.00
    assert m.total_cost_usd == pytest.approx(3.0, abs=0.01)


def test_intent_persona_and_tool_counts() -> None:
    turns = [
        _turn(intent="triage_request", persona="ops_associate",
              tool_calls=[{"name": "lookup_shipment"}]),
        _turn(intent="follow_up", persona="ops_associate",
              tool_calls=[]),
        _turn(intent="triage_request", persona="finance_partner",
              tool_calls=[
                  {"name": "lookup_shipment"},
                  {"name": "search_sops"},
              ]),
    ]
    m = aggregate_metrics(turns)
    assert m.intent_counts == {"triage_request": 2, "follow_up": 1}
    assert m.persona_counts == {"ops_associate": 2, "finance_partner": 1}
    assert m.tool_counts == {"lookup_shipment": 2, "search_sops": 1}


def test_safety_findings_aggregation() -> None:
    turns = [
        _turn(
            safety_findings=[
                {"severity": "high", "pattern_name": "commitment_language", "matched_text": "x"},
                {"severity": "high", "pattern_name": "commitment_language", "matched_text": "y"},
            ]
        ),
        _turn(
            safety_findings=[
                {"severity": "medium", "pattern_name": "hard_date_commitment", "matched_text": "z"}
            ]
        ),
    ]
    m = aggregate_metrics(turns)
    assert m.safety_counts_by_severity == {"high": 2, "medium": 1}
    assert m.safety_counts_by_pattern == {"commitment_language": 2, "hard_date_commitment": 1}


def test_error_count() -> None:
    turns = [
        _turn(error=None),
        _turn(error="ValueError: x"),
        _turn(error=None),
    ]
    m = aggregate_metrics(turns)
    assert m.n_errors == 1


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def test_alert_for_recent_high_severity_safety() -> None:
    turns = [
        _turn(
            ts=time.time(),
            safety_findings=[
                {
                    "severity": "high",
                    "pattern_name": "fabricated_sop_citation",
                    "matched_text": "sop-fake.md",
                }
            ],
        )
    ]
    alerts = derive_alerts(turns)
    assert len(alerts) >= 1
    assert any(a.severity == "high" for a in alerts)
    assert any("fabricated_sop_citation" in a.detail for a in alerts)


def test_alert_for_p95_latency_breach() -> None:
    # Need enough slow turns that the 95th-percentile rank lands on one.
    # With nearest-rank percentile, 5%+ of values must exceed the threshold.
    turns = [_turn(total_duration_ms=500) for _ in range(15)]
    turns.extend(_turn(total_duration_ms=12_000) for _ in range(5))
    th = AlertThresholds(p95_latency_ms=8_000, recent_window_hours=24)
    alerts = derive_alerts(turns, th)
    assert any("P95 latency" in a.title for a in alerts)


def test_no_alerts_when_clean() -> None:
    turns = [_turn(total_duration_ms=500) for _ in range(10)]
    alerts = derive_alerts(turns)
    assert alerts == []


def test_old_turns_outside_window_are_ignored() -> None:
    # 10 fresh turns are clean, but 1 old turn has a high-severity finding.
    fresh_ts = time.time()
    old_ts = fresh_ts - 25 * 3600  # 25 hours ago
    turns = [_turn(ts=fresh_ts, total_duration_ms=500) for _ in range(5)]
    turns.append(
        _turn(
            ts=old_ts,
            safety_findings=[
                {"severity": "high", "pattern_name": "x", "matched_text": "y"}
            ],
        )
    )
    th = AlertThresholds(recent_window_hours=24)
    alerts = derive_alerts(turns, th)
    # The old finding should NOT appear because it's outside the 24h window.
    assert all("safety finding" not in a.title for a in alerts)


def test_error_rate_alert() -> None:
    # 5 errors in 10 turns = 50% error rate
    turns = [_turn(error="ValueError") for _ in range(5)] + [_turn() for _ in range(5)]
    th = AlertThresholds(error_rate_pct=10.0)
    alerts = derive_alerts(turns, th)
    assert any("Error rate" in a.title for a in alerts)
