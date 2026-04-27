"""Session Inspector page — browse and replay any logged session."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Streamlit pages don't share sys.path with the entry script — re-set up here.
_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT / "src", _ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

from _helpers import fmt_ms, fmt_ts  # noqa: E402, F401

from freight_copilot.monitoring import list_sessions, read_session  # noqa: E402

st.set_page_config(page_title="Sessions · Triage Copilot", page_icon="🔍", layout="wide")

st.title("🔍 Sessions")
st.caption("Browse every logged session. Pick one to replay turn-by-turn.")

sessions = list_sessions()
if not sessions:
    st.info("No sessions logged yet — run a triage in the Triage Console first.")
    st.stop()


# ---------------------------------------------------------------------------
# Sidebar — pick a session
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Sessions on disk")
    st.caption(f"{len(sessions)} session(s) — most recent first")

    # Build readable labels and store thread_ids
    label_to_id: dict[str, str] = {}
    for s in sessions:
        flag = " 🔴" if s["n_safety_high"] else ""
        flag += " ⚠" if s["had_error"] else ""
        label = (
            f"{s['thread_id'][:8]}…  "
            f"({s['n_turns']} turn{'s' if s['n_turns'] != 1 else ''})  "
            f"· {s['persona']}{flag}"
        )
        label_to_id[label] = s["thread_id"]

    chosen_label = st.selectbox(
        "Pick a session", options=list(label_to_id), index=0, key="session_picker"
    )
    chosen_thread_id = label_to_id[chosen_label]


# ---------------------------------------------------------------------------
# Header — session-level summary
# ---------------------------------------------------------------------------

session_meta = next(s for s in sessions if s["thread_id"] == chosen_thread_id)
turns = read_session(chosen_thread_id)

st.subheader(f"Session `{chosen_thread_id}`")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Turns", session_meta["n_turns"])
m2.metric("Persona", session_meta["persona"])
m3.metric("Model", session_meta["model"][:30])
m4.metric("First", fmt_ts(session_meta["first_ts"]))
m5.metric("Last", fmt_ts(session_meta["last_ts"]))

if session_meta["n_safety_high"] or session_meta["had_error"]:
    badges = []
    if session_meta["n_safety_high"]:
        badges.append(f"🔴 {session_meta['n_safety_high']} high-severity safety finding(s)")
    if session_meta["had_error"]:
        badges.append("⚠ this session had at least one error")
    st.warning("  ·  ".join(badges))

st.divider()


# ---------------------------------------------------------------------------
# Turn-by-turn replay
# ---------------------------------------------------------------------------

for t in turns:
    n = t.get("turn_index", "?")
    intent = t.get("intent") or "—"
    persona = t.get("persona") or "—"
    latency = fmt_ms(t.get("total_duration_ms"))
    in_tok = t.get("input_tokens") or "—"
    out_tok = t.get("output_tokens") or "—"

    st.markdown(
        f"### Turn {n}  ·  `intent: {intent}`  ·  `persona: {persona}`  ·  "
        f"latency {latency}  ·  tokens {in_tok}/{out_tok}"
    )

    with st.chat_message("user"):
        st.markdown(t.get("user_input") or "—")

    with st.chat_message("assistant"):
        # Tool trace
        tool_calls = t.get("tool_calls") or []
        if tool_calls:
            with st.expander(f"Tool trace ({len(tool_calls)} call(s))"):
                for tc in tool_calls:
                    st.markdown(
                        f"**`{tc.get('name', '?')}`** "
                        f"`{json.dumps(tc.get('args', {}), ensure_ascii=False)}` "
                        f"— {fmt_ms(tc.get('duration_ms'))}"
                    )
                    preview = tc.get("result_preview", "")
                    if preview:
                        st.code(preview[:1200], language="json")

        # Safety findings
        findings = t.get("safety_findings") or []
        if findings:
            with st.expander(f"Safety findings ({len(findings)})", expanded=True):
                for f in findings:
                    sev = f.get("severity", "?")
                    badge = "🔴" if sev == "high" else ("🟡" if sev == "medium" else "🟢")
                    pat = f.get("pattern_name") or f.get("pattern") or "?"
                    matched = (f.get("matched_text") or f.get("matched") or "")
                    st.markdown(f"{badge} **{pat}** [{sev}] — `{matched[:120]}`")

        # Error
        if t.get("error"):
            st.error(f"❌ {t['error']}")

        # Final response
        if t.get("final_response"):
            st.markdown(t["final_response"])

    st.divider()


# ---------------------------------------------------------------------------
# Raw JSONL
# ---------------------------------------------------------------------------

with st.expander("Raw JSONL (one record per turn)"):
    st.code(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in turns)[:20_000],
        language="json",
    )
