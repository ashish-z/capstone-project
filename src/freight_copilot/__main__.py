"""CLI entry point: `python -m freight_copilot`.

Multi-turn loop with visible tool calls, intent classification, safety
findings, and JSONL session logging. Each turn shows the classified intent
inline. Switch personas mid-session with `/role <name>` (try `/role` to list).
"""

from __future__ import annotations

import json
import sys

from freight_copilot.agent import AgentSession
from freight_copilot.prompts.personas import list_personas

BANNER = """
================================================================
  Freight Operations Triage Copilot
  Type your question. Use Ctrl-D, 'exit', or 'quit' to end.
  Commands: /reset  /role <name>  /role  (lists personas)
================================================================
"""


def _print_event(event: dict) -> None:
    etype = event["type"]
    if etype == "intent":
        print(
            f"  [intent] {event['intent']}  "
            f"(confidence={event['confidence']:.2f}, margin={event['margin']:.2f})"
        )
    elif etype == "tool_call":
        args = json.dumps(event["args"], ensure_ascii=False)
        print(f"  [tool→]  {event['name']}({args})")
    elif etype == "tool_result":
        print(f"  [tool←]  {event['name']}: {event['result']}")
    elif etype == "final":
        print("\n" + "-" * 64)
        print(event["text"])
        print("-" * 64)
    elif etype == "safety":
        # Show safety findings between the tool calls and the final response.
        print(f"\n  ⚠ {event['summary']}")
        for f in event["findings"]:
            sev_marker = "✗" if f["severity"] == "high" else "!"
            print(
                f"  {sev_marker} [{f['severity']}] {f['pattern']}: "
                f"{f['matched'][:80]!r}"
            )
    elif etype == "error":
        print(f"\n[error] {event['message']}", file=sys.stderr)


def _print_personas() -> None:
    print("\n  Available personas:")
    for p in list_personas():
        print(f"    {p.name:18s} {p.role_label:35s} — {p.description}")


def _session_header(session: AgentSession) -> None:
    print(f"  session: {session.thread_id}  (persona: {session.persona})")
    print(f"  log:     logs/session-{session.thread_id}.jsonl")


def main() -> int:
    print(BANNER)
    session = AgentSession()
    _session_header(session)
    _print_personas()

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("bye.")
            return 0
        if user_input == "/reset":
            session = AgentSession(persona=session.persona)
            print()
            _session_header(session)
            continue
        if user_input.startswith("/role"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 1:
                _print_personas()
                print(f"  current: {session.persona}")
                continue
            new_persona = parts[1].strip()
            try:
                session.set_persona(new_persona)
                print(f"  ✓ persona switched to '{session.persona}'")
            except Exception as exc:  # noqa: BLE001
                print(f"  [error] {exc}", file=sys.stderr)
            continue

        try:
            for event in session.stream_turn(user_input):
                _print_event(event)
        except Exception as exc:  # noqa: BLE001 — top-level CLI safety net
            print(f"\n[error] {type(exc).__name__}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
