"""Read session JSONL logs and produce aggregate metrics + alerts.

This is the data layer for the Streamlit monitoring dashboard. We read
every line in `logs/session-*.jsonl`, normalize into a flat list of turn
records, and offer:

  read_turns()              — flat list of all logged turns, sorted by ts
  aggregate_metrics(turns)  — summary stats (counts, latency, tokens, etc.)
  derive_alerts(turns, ...) — active alerts (recent safety findings,
                              latency breaches, error spikes, cost burn)

Cost figures use the public Anthropic price list for Claude Haiku 4.5
($1/MTok input, $5/MTok output) — see ANTHROPIC_HAIKU_45_USD_PER_MTOK
below; override if model changes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _REPO_ROOT / "logs"

# Public Anthropic prices, USD per million tokens. Update if the model changes.
ANTHROPIC_HAIKU_45_USD_PER_MTOK = (1.0, 5.0)  # (input, output)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _log_files() -> list[Path]:
    if not _LOG_DIR.exists():
        return []
    return sorted(_LOG_DIR.glob("session-*.jsonl"))


def read_turns() -> list[dict[str, Any]]:
    """Read every JSONL line across all session files. Returns turns sorted
    by timestamp ascending. Malformed lines are skipped silently."""
    turns: list[dict[str, Any]] = []
    for path in _log_files():
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                turns.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    turns.sort(key=lambda t: t.get("ts", 0.0))
    return turns


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


@dataclass
class Metrics:
    """Aggregate stats across a window of turns."""

    n_turns: int = 0
    n_sessions: int = 0
    n_errors: int = 0

    latency_ms_p50: float = 0.0
    latency_ms_p95: float = 0.0
    latency_ms_avg: float = 0.0

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0

    intent_counts: dict[str, int] = field(default_factory=dict)
    persona_counts: dict[str, int] = field(default_factory=dict)
    tool_counts: dict[str, int] = field(default_factory=dict)
    safety_counts_by_severity: dict[str, int] = field(default_factory=dict)
    safety_counts_by_pattern: dict[str, int] = field(default_factory=dict)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(pct / 100 * (len(s) - 1)))))
    return s[k]


def aggregate_metrics(
    turns: list[dict[str, Any]],
    price_per_mtok: tuple[float, float] = ANTHROPIC_HAIKU_45_USD_PER_MTOK,
) -> Metrics:
    m = Metrics()
    if not turns:
        return m

    m.n_turns = len(turns)
    m.n_sessions = len({t.get("thread_id") for t in turns if t.get("thread_id")})
    m.n_errors = sum(1 for t in turns if t.get("error"))

    latencies = [
        t["total_duration_ms"]
        for t in turns
        if isinstance(t.get("total_duration_ms"), (int, float)) and t["total_duration_ms"] > 0
    ]
    if latencies:
        m.latency_ms_p50 = _percentile(latencies, 50)
        m.latency_ms_p95 = _percentile(latencies, 95)
        m.latency_ms_avg = sum(latencies) / len(latencies)

    in_tok = sum(int(t.get("input_tokens") or 0) for t in turns)
    out_tok = sum(int(t.get("output_tokens") or 0) for t in turns)
    m.total_input_tokens = in_tok
    m.total_output_tokens = out_tok
    p_in, p_out = price_per_mtok
    m.total_cost_usd = (in_tok / 1_000_000) * p_in + (out_tok / 1_000_000) * p_out

    for t in turns:
        intent = t.get("intent") or "unknown"
        m.intent_counts[intent] = m.intent_counts.get(intent, 0) + 1

        persona = t.get("persona") or "unknown"
        m.persona_counts[persona] = m.persona_counts.get(persona, 0) + 1

        for tc in t.get("tool_calls", []) or []:
            name = tc.get("name", "unknown")
            m.tool_counts[name] = m.tool_counts.get(name, 0) + 1

        for f in t.get("safety_findings", []) or []:
            sev = f.get("severity", "unknown")
            pat = f.get("pattern_name") or f.get("pattern") or "unknown"
            m.safety_counts_by_severity[sev] = m.safety_counts_by_severity.get(sev, 0) + 1
            m.safety_counts_by_pattern[pat] = m.safety_counts_by_pattern.get(pat, 0) + 1

    return m


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


@dataclass
class Alert:
    severity: str  # "high" | "medium" | "low"
    title: str
    detail: str


@dataclass
class AlertThresholds:
    """Threshold knobs for derive_alerts. Defaults match the Phase 1
    success-metric targets (P95 latency < 8s, etc.)."""

    p95_latency_ms: int = 8_000
    error_rate_pct: float = 5.0
    cost_burn_usd_per_hour: float = 1.0
    recent_window_hours: int = 24


def derive_alerts(
    turns: list[dict[str, Any]],
    thresholds: AlertThresholds | None = None,
) -> list[Alert]:
    """Return active alerts. Looks at the last `recent_window_hours` of turns."""
    th = thresholds or AlertThresholds()
    cutoff = time.time() - th.recent_window_hours * 3600
    recent = [t for t in turns if t.get("ts", 0) >= cutoff]
    alerts: list[Alert] = []

    if not recent:
        return alerts

    # 1. Recent high-severity safety findings — every one is an alert.
    for t in recent:
        for f in t.get("safety_findings", []) or []:
            if f.get("severity") == "high":
                alerts.append(
                    Alert(
                        severity="high",
                        title="High-severity safety finding",
                        detail=(
                            f"thread {t.get('thread_id')[:8]}…  "
                            f"{f.get('pattern_name') or f.get('pattern')}: "
                            f"{(f.get('matched_text') or f.get('matched') or '')!r}"
                        ),
                    )
                )

    # 2. Latency P95 over threshold
    latencies = [
        t["total_duration_ms"]
        for t in recent
        if isinstance(t.get("total_duration_ms"), (int, float)) and t["total_duration_ms"] > 0
    ]
    if latencies and _percentile(latencies, 95) > th.p95_latency_ms:
        alerts.append(
            Alert(
                severity="medium",
                title=f"P95 latency above {th.p95_latency_ms / 1000:.1f}s threshold",
                detail=(
                    f"P95 last {th.recent_window_hours}h: "
                    f"{_percentile(latencies, 95) / 1000:.1f}s "
                    f"(over {len(latencies)} turns)"
                ),
            )
        )

    # 3. Error rate
    if recent:
        n_err = sum(1 for t in recent if t.get("error"))
        rate = (n_err / len(recent)) * 100
        if rate > th.error_rate_pct:
            alerts.append(
                Alert(
                    severity="high",
                    title=f"Error rate {rate:.1f}% above {th.error_rate_pct:.1f}% threshold",
                    detail=f"{n_err} errors in last {len(recent)} turns",
                )
            )

    # 4. Cost burn
    metrics = aggregate_metrics(recent)
    if th.recent_window_hours > 0:
        burn = metrics.total_cost_usd / th.recent_window_hours
        if burn > th.cost_burn_usd_per_hour:
            alerts.append(
                Alert(
                    severity="medium",
                    title=f"Cost burn ${burn:.2f}/h over ${th.cost_burn_usd_per_hour:.2f}/h threshold",
                    detail=(
                        f"${metrics.total_cost_usd:.2f} across last "
                        f"{th.recent_window_hours}h ({metrics.n_turns} turns)"
                    ),
                )
            )

    return alerts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def list_sessions() -> list[dict[str, Any]]:
    """Per-session summary: thread_id, n_turns, first/last ts, persona, etc."""
    by_thread: dict[str, list[dict[str, Any]]] = {}
    for t in read_turns():
        by_thread.setdefault(t.get("thread_id", "unknown"), []).append(t)

    sessions: list[dict[str, Any]] = []
    for tid, turns in by_thread.items():
        if not turns:
            continue
        first = turns[0]
        last = turns[-1]
        sessions.append(
            {
                "thread_id": tid,
                "n_turns": len(turns),
                "first_ts": first.get("ts"),
                "last_ts": last.get("ts"),
                "persona": last.get("persona") or first.get("persona") or "—",
                "model": first.get("model") or "—",
                "n_safety_high": sum(
                    1
                    for t in turns
                    for f in (t.get("safety_findings") or [])
                    if f.get("severity") == "high"
                ),
                "had_error": any(t.get("error") for t in turns),
            }
        )
    sessions.sort(key=lambda s: s.get("last_ts") or 0, reverse=True)
    return sessions


def read_session(thread_id: str) -> list[dict[str, Any]]:
    """Read a single session's turn records, in turn order."""
    path = _LOG_DIR / f"session-{thread_id}.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    out.sort(key=lambda t: t.get("turn_index", 0))
    return out
