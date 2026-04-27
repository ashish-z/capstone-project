"""CLI entry point: `python -m freight_copilot`.

Phase 3 ships a multi-turn loop with visible tool calls and per-session JSONL
logging. The same session (= one thread_id) preserves message history across
turns, so the user can ask follow-up questions naturally.
"""

from __future__ import annotations

import json
import sys

from freight_copilot.agent import AgentSession

BANNER = """
================================================================
  Freight Operations Triage Copilot — Phase 3 (multi-turn)
  Type your question. Use Ctrl-D, 'exit', or 'quit' to end.
  Type '/reset' to start a fresh session.
================================================================
"""


def _print_event(event: dict) -> None:
    etype = event["type"]
    if etype == "tool_call":
        args = json.dumps(event["args"], ensure_ascii=False)
        print(f"  [tool→]  {event['name']}({args})")
    elif etype == "tool_result":
        print(f"  [tool←]  {event['name']}: {event['result']}")
    elif etype == "final":
        print("\n" + "-" * 64)
        print(event["text"])
        print("-" * 64)
    elif etype == "error":
        print(f"\n[error] {event['message']}", file=sys.stderr)


def main() -> int:
    print(BANNER)
    session = AgentSession()
    print(f"  session: {session.thread_id}")
    print(f"  log:     logs/session-{session.thread_id}.jsonl\n")

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
            session = AgentSession()
            print(f"  new session: {session.thread_id}")
            continue

        try:
            for event in session.stream_turn(user_input):
                _print_event(event)
        except Exception as exc:  # noqa: BLE001 — top-level CLI safety net
            print(f"\n[error] {type(exc).__name__}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
