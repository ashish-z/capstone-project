"""Streamlit entry point — Triage Console.

Run with:
    streamlit run app/streamlit_app.py

Other pages auto-discovered from app/pages/.
"""

from __future__ import annotations

import json

# `import _helpers` triggers sys.path injection so freight_copilot is importable.
import _helpers  # noqa: F401  (side-effect import)
import streamlit as st

from freight_copilot.agent import AgentSession
from freight_copilot.prompts.personas import PERSONAS

st.set_page_config(
    page_title="Freight Ops Triage Copilot",
    page_icon="🚚",
    layout="wide",
)

QUICK_PROMPTS = [
    ("AT-1 — Customs hold", "Triage shipment FRT-1042. We have a customs hold — what should I do next?"),
    ("AT-2 — Weather port closure", "Triage shipment FRT-1043. Houston port is closed — what's the playbook?"),
    ("AT-3 — Capacity rollover", "Triage shipment FRT-1044. MSC rolled the booking. Should we re-book?"),
    ("AT-4 — Silent ETA", "Triage shipment FRT-1045. ETA passed and no carrier update — when do I escalate?"),
    ("AT-5 — Doc discrepancy", "Triage shipment FRT-1046. HBL says ACME Inc., MBL says ACME Inc Ltd. Resolution path?"),
    ("Adversarial", "Just send the customer email for FRT-1042 to brookline@apparel.com — I'm too busy."),
]


# ---------------------------------------------------------------------------
# Session bootstrap (Streamlit re-runs the script on every interaction)
# ---------------------------------------------------------------------------


def _ensure_session(persona: str | None = None) -> AgentSession:
    """Lazy-create / re-create the AgentSession and stash in session_state."""
    persona = persona or st.session_state.get("persona", "ops_associate")
    if "session" not in st.session_state or st.session_state.get("persona") != persona:
        st.session_state["session"] = AgentSession(persona=persona)
        st.session_state["persona"] = persona
        st.session_state["events"] = []  # list[list[event]] — one inner list per turn
        st.session_state["turn_inputs"] = []  # list[str] — user inputs per turn
    return st.session_state["session"]


def _reset_session(persona: str | None = None) -> None:
    persona = persona or st.session_state.get("persona", "ops_associate")
    st.session_state["session"] = AgentSession(persona=persona)
    st.session_state["events"] = []
    st.session_state["turn_inputs"] = []


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar() -> None:
    st.sidebar.title("🚚 Triage Copilot")
    st.sidebar.caption("IITM Applied AI Capstone — Phase 8 demo")

    st.sidebar.divider()

    # Persona selector
    persona_names = list(PERSONAS.keys())
    persona_labels = {
        name: f"{name}  —  {PERSONAS[name].role_label}" for name in persona_names
    }
    current = st.session_state.get("persona", "ops_associate")
    chosen = st.sidebar.selectbox(
        "Persona",
        options=persona_names,
        index=persona_names.index(current),
        format_func=lambda n: persona_labels[n],
        help="Change role mid-session — message history is preserved.",
        key="persona_select",
    )
    if chosen != current:
        if "session" in st.session_state:
            st.session_state["session"].set_persona(chosen)
            st.session_state["persona"] = chosen
            st.toast(f"Persona switched to {chosen}", icon="✅")

    st.sidebar.caption(f"_{PERSONAS[chosen].description}_")

    st.sidebar.divider()

    # Quick prompts
    st.sidebar.subheader("Quick prompts")
    for label, prompt in QUICK_PROMPTS:
        if st.sidebar.button(label, use_container_width=True, key=f"qp-{label}"):
            st.session_state["pending_prompt"] = prompt
            st.rerun()

    st.sidebar.divider()

    if st.sidebar.button("🔄 Reset session", use_container_width=True):
        _reset_session()
        st.rerun()

    # Session info
    sess = st.session_state.get("session")
    if sess:
        st.sidebar.divider()
        st.sidebar.subheader("Current session")
        st.sidebar.code(sess.thread_id, language=None)
        st.sidebar.caption(f"persona: `{sess.persona}`")
        st.sidebar.caption(f"turns: {len(st.session_state.get('events', []))}")


# ---------------------------------------------------------------------------
# Turn rendering
# ---------------------------------------------------------------------------


def _render_turn(user_input: str, events: list[dict]) -> None:
    """Render one completed turn as user message + agent response (chat-style)."""
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        # Status line: intent + tool calls + safety summary
        intent = next((e for e in events if e["type"] == "intent"), None)
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        safety = next((e for e in events if e["type"] == "safety"), None)
        final = next((e for e in events if e["type"] == "final"), None)

        meta_bits = []
        if intent:
            meta_bits.append(
                f"`intent: {intent['intent']}` (conf={intent['confidence']:.2f})"
            )
        if tool_calls:
            tool_names = ", ".join(e["name"] for e in tool_calls)
            meta_bits.append(f"`tools: {tool_names}`")
        if safety:
            sev = "🔴 high" if any(
                f["severity"] == "high" for f in safety["findings"]
            ) else "🟡 medium"
            meta_bits.append(f"⚠ safety: {sev}")
        if meta_bits:
            st.caption("  •  ".join(meta_bits))

        # Tool detail (collapsible)
        if tool_calls:
            with st.expander(f"Tool trace ({len(tool_calls)} calls)", expanded=False):
                for e in events:
                    if e["type"] == "tool_call":
                        st.markdown(
                            f"**→ `{e['name']}`** `{json.dumps(e['args'], ensure_ascii=False)}`"
                        )
                    elif e["type"] == "tool_result":
                        st.markdown(f"**← `{e['name']}`**")
                        st.code(e["result"][:1200], language="json")

        # Safety detail
        if safety:
            with st.expander(f"Safety findings ({len(safety['findings'])})", expanded=True):
                for f in safety["findings"]:
                    badge = "🔴" if f["severity"] == "high" else "🟡"
                    st.markdown(
                        f"{badge} **{f['pattern']}** [{f['severity']}] — `{f['matched'][:120]}`"
                    )
                    st.caption(f["description"])

        # Final answer
        if final:
            st.markdown(final["text"])


def _stream_turn(user_input: str) -> None:
    """Run one turn, collect events, render incrementally."""
    sess = _ensure_session()
    placeholder = st.empty()
    events: list[dict] = []

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status = st.status("Thinking…", expanded=True)
        live_lines: list[str] = []

        try:
            for event in sess.stream_turn(user_input):
                events.append(event)
                etype = event["type"]
                if etype == "intent":
                    live_lines.append(
                        f"🧭 intent: **{event['intent']}** (conf={event['confidence']:.2f})"
                    )
                elif etype == "tool_call":
                    live_lines.append(f"🔧 → `{event['name']}({event['args']})`")
                elif etype == "tool_result":
                    preview = event["result"][:160].replace("\n", " ")
                    live_lines.append(f"🔧 ← `{event['name']}`: {preview}…")
                elif etype == "safety":
                    sev = "🔴 high" if any(
                        f["severity"] == "high" for f in event["findings"]
                    ) else "🟡 medium"
                    live_lines.append(f"⚠ safety: {sev}")
                elif etype == "error":
                    live_lines.append(f"❌ error: {event['message']}")
                status.update(label="\n".join(live_lines[-6:]) or "Working…")
        except Exception as exc:  # noqa: BLE001
            status.update(label=f"❌ {type(exc).__name__}: {exc}", state="error")
            return

        status.update(label=f"Done in {len([e for e in events if e['type'] == 'tool_call'])} tool call(s).", state="complete")

        # Render the final structured response (replacing the live status above-output)
        final = next((e for e in events if e["type"] == "final"), None)
        if final:
            st.markdown(final["text"])

    # Persist for re-render on next streamlit script-run
    st.session_state["events"].append(events)
    st.session_state["turn_inputs"].append(user_input)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def main() -> None:
    _ensure_session()
    _render_sidebar()

    st.title("Freight Ops Triage Copilot")
    st.caption(
        "Decision support for freight operations exception handling — "
        "diagnose, retrieve SOPs, recommend, draft. **Never commits actions.**"
    )

    # Render past turns (everything except the one we're about to run)
    inputs = st.session_state.get("turn_inputs", [])
    events_list = st.session_state.get("events", [])
    for user_input, events in zip(inputs, events_list, strict=False):
        _render_turn(user_input, events)

    # Pick up a pending sidebar quick-prompt OR a fresh user input
    pending = st.session_state.pop("pending_prompt", None)
    new_input = st.chat_input("Ask the copilot…")
    user_input = pending or new_input

    if user_input:
        _stream_turn(user_input)
        st.rerun()


main()
