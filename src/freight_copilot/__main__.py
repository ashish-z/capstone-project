"""CLI entry point: `python -m freight_copilot`.

Phase 2 ships a minimal single-shot loop. Multi-turn memory comes in Phase 3.
"""

from __future__ import annotations

import sys

from freight_copilot.agent import run_once

BANNER = """
================================================================
  Freight Operations Triage Copilot — Phase 2 (single-turn)
  Type your question. Use Ctrl-D or 'exit' to quit.
================================================================
"""


def main() -> int:
    print(BANNER)
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

        try:
            response = run_once(user_input)
        except Exception as exc:  # noqa: BLE001 — top-level CLI safety net
            print(f"\n[error] {type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        print("\n" + "-" * 64)
        print(response)
        print("-" * 64)


if __name__ == "__main__":
    sys.exit(main())
