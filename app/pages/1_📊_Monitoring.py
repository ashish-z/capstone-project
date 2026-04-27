"""Monitoring Dashboard page.

Aggregates everything in logs/session-*.jsonl into a live operational view:
KPIs, alerts, distributions, recent timeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit pages don't share sys.path with the entry script — re-set up here.
_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT / "src", _ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

from _helpers import fmt_ms, fmt_usd  # noqa: E402, F401

from freight_copilot.monitoring import (  # noqa: E402
    AlertThresholds,
    aggregate_metrics,
    derive_alerts,
    read_turns,
)

st.set_page_config(page_title="Monitoring · Triage Copilot", page_icon="📊", layout="wide")

st.title("📊 Monitoring")
st.caption("Aggregated metrics across every session JSONL on disk.")


# ---------------------------------------------------------------------------
# Refresh + read
# ---------------------------------------------------------------------------

c_top1, c_top2 = st.columns([1, 5])
with c_top1:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
with c_top2:
    st.caption("Reload from disk to pick up new sessions / turns.")

turns = read_turns()
if not turns:
    st.info("No session logs yet. Run a triage in the **Triage Console** first.")
    st.stop()

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

st.subheader("Active alerts (last 24h)")

alerts = derive_alerts(turns, AlertThresholds(recent_window_hours=24))
if not alerts:
    st.success("All clear — no active alerts in the last 24 hours.")
else:
    for a in alerts:
        if a.severity == "high":
            st.error(f"🔴 **{a.title}** — {a.detail}")
        elif a.severity == "medium":
            st.warning(f"🟡 **{a.title}** — {a.detail}")
        else:
            st.info(f"🟢 **{a.title}** — {a.detail}")

st.divider()

# ---------------------------------------------------------------------------
# KPI strip (all-time)
# ---------------------------------------------------------------------------

m = aggregate_metrics(turns)

st.subheader("All-time metrics")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Sessions", m.n_sessions)
k2.metric("Turns", m.n_turns)
k3.metric("P95 latency", fmt_ms(m.latency_ms_p95))
k4.metric("Median latency", fmt_ms(m.latency_ms_p50))
k5.metric("Cost (Haiku 4.5)", fmt_usd(m.total_cost_usd))

st.caption(
    f"Tokens: **{m.total_input_tokens:,}** in  /  **{m.total_output_tokens:,}** out  "
    f"·  errors: **{m.n_errors}** of {m.n_turns} ({(m.n_errors / max(m.n_turns, 1)) * 100:.1f}%)"
)

st.divider()

# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Intent distribution")
    if m.intent_counts:
        st.bar_chart(m.intent_counts, horizontal=True)
    else:
        st.caption("—")

with c2:
    st.subheader("Persona usage")
    if m.persona_counts:
        st.bar_chart(m.persona_counts, horizontal=True)
    else:
        st.caption("—")

with c3:
    st.subheader("Tool calls")
    if m.tool_counts:
        st.bar_chart(m.tool_counts, horizontal=True)
    else:
        st.caption("—")

st.divider()

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

st.subheader("Safety findings")
sc1, sc2 = st.columns(2)

with sc1:
    st.markdown("**By severity**")
    if m.safety_counts_by_severity:
        st.bar_chart(m.safety_counts_by_severity, horizontal=True)
    else:
        st.success("Clean — no safety findings logged across all turns.")

with sc2:
    st.markdown("**By pattern**")
    if m.safety_counts_by_pattern:
        st.bar_chart(m.safety_counts_by_pattern, horizontal=True)
    else:
        st.caption("—")

st.divider()

# ---------------------------------------------------------------------------
# Per-turn latency timeline
# ---------------------------------------------------------------------------

st.subheader("Latency timeline")
import pandas as _pd  # local import — avoids pandas cost on cold start

rows = [
    {
        "turn_idx": i,
        "ts": t.get("ts"),
        "latency_ms": t.get("total_duration_ms") or 0,
        "intent": t.get("intent") or "—",
        "persona": t.get("persona") or "—",
    }
    for i, t in enumerate(turns)
]
df = _pd.DataFrame(rows)
if not df.empty:
    chart_df = df.set_index("turn_idx")["latency_ms"]
    st.line_chart(chart_df)
    st.caption(
        f"P95 = **{fmt_ms(m.latency_ms_p95)}** "
        f"(target: P95 < 8 s per Phase 1 success metrics)"
    )

st.divider()

# ---------------------------------------------------------------------------
# Raw turns table
# ---------------------------------------------------------------------------

with st.expander("Raw turns table", expanded=False):
    cols = [
        "ts",
        "thread_id",
        "turn_index",
        "persona",
        "intent",
        "total_duration_ms",
        "input_tokens",
        "output_tokens",
        "tool_calls",
        "safety_findings",
        "error",
    ]
    raw_rows = []
    for t in turns:
        raw_rows.append(
            {
                "ts": t.get("ts"),
                "thread_id": (t.get("thread_id") or "")[:12],
                "turn_index": t.get("turn_index"),
                "persona": t.get("persona") or "—",
                "intent": t.get("intent") or "—",
                "total_duration_ms": t.get("total_duration_ms"),
                "input_tokens": t.get("input_tokens"),
                "output_tokens": t.get("output_tokens"),
                "tool_calls": ", ".join(
                    tc.get("name", "?") for tc in (t.get("tool_calls") or [])
                ),
                "safety_findings": len(t.get("safety_findings") or []),
                "error": (t.get("error") or "")[:80],
            }
        )
    st.dataframe(_pd.DataFrame(raw_rows, columns=cols), use_container_width=True)
