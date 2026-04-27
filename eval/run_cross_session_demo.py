"""Phase 6 demo — cross-session memory + correction handling.

Demonstrates that memory persists across separate AgentSession instances:

  1. Reset memory db, then re-seed with the historical notes.
  2. Session A: triage AT-1 (FRT-1042). Agent uses recall tools, sees the
     seeded customer note about Aurora's slow CI response, and applies
     it. User then corrects the customer tier ("actually Platinum, not
     Gold") — this turn is detected as `correction` intent and persisted.
  3. Session B: a brand-new AgentSession (different thread_id). Triage
     same shipment. The agent must see Session A's correction surfaced
     via recall_customer_history and apply it without being told again.

The point is to show three things working together:
  - Intent classification (the correction is detected automatically).
  - Long-term memory (corrections persist across sessions).
  - Recall tools (the new agent uses them on its own).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from freight_copilot.agent import AgentSession  # noqa: E402
from freight_copilot.memory.seed import seed_all  # noqa: E402

SESSION_A_TURNS = [
    "Triage shipment FRT-1042. Quick — what should I do next?",
    "Actually, Brookline Apparel got promoted to Platinum tier last week, not Gold. Update for any future triages.",
]

SESSION_B_TURNS = [
    "Looking at FRT-1042 again. Anything I should know about this customer that affects how I triage?",
]


def _print_event(event: dict) -> None:
    etype = event["type"]
    if etype == "intent":
        print(
            f"  [intent]  {event['intent']}  "
            f"(conf={event['confidence']:.2f}, margin={event['margin']:.2f})"
        )
    elif etype == "tool_call":
        print(f"  [tool→]   {event['name']}({event['args']})")
    elif etype == "tool_result":
        print(f"  [tool←]   {event['name']}: {event['result'][:160]}…")
    elif etype == "safety":
        print(f"  [safety]  {event['summary']}")
    elif etype == "final":
        print("\n  AGENT:")
        for line in event["text"].splitlines():
            print(f"    {line}")
    elif etype == "error":
        print(f"  [error]   {event['message']}")


def run_session(label: str, turns: list[str]) -> str:
    session = AgentSession()
    print(f"\n{'=' * 76}")
    print(f"SESSION {label} — thread_id={session.thread_id}")
    print(f"{'=' * 76}")
    for i, prompt in enumerate(turns, start=1):
        print(f"\n────────── {label}.{i} ──────────")
        print(f"USER: {prompt}\n")
        for event in session.stream_turn(prompt):
            _print_event(event)
    return session.thread_id


def main() -> None:
    print("Re-seeding long-term memory db with historical notes…")
    stats = seed_all()
    print(f"Seeded: {stats}")

    a_id = run_session("A", SESSION_A_TURNS)
    print(f"\n[Session A complete. Correction persisted to memory db.]")
    b_id = run_session("B", SESSION_B_TURNS)
    print(f"\n[Session B complete. Started fresh thread_id={b_id} — no in-process state from A.]")

    print(f"\n{'=' * 76}")
    print(
        "If Session B mentioned 'Platinum' (or referenced the tier promotion) "
        "in its triage, long-term memory worked across sessions."
    )
    print(f"  Session A log: logs/session-{a_id}.jsonl")
    print(f"  Session B log: logs/session-{b_id}.jsonl")


if __name__ == "__main__":
    main()
