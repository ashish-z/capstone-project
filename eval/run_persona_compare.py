"""Phase 7 demo — same prompt across all three personas, side-by-side.

Picks a single AT-3 (capacity rollover) prompt and runs it through:
  ops_associate    → tactical, action-sequencing
  finance_partner  → cost framing, demurrage, rate deltas
  customer_lead    → draft-quality, tone calibration

Writes:
  docs/phase7-persona-compare.md         — human-readable side-by-side
  docs/phase7-persona-compare.json       — raw machine-readable record
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from freight_copilot.agent import AgentSession  # noqa: E402
from freight_copilot.prompts.personas import PERSONAS  # noqa: E402

PROMPT = (
    "Triage shipment FRT-1044. MSC rolled the booking by 7 days. The customer "
    "(Hanseatic Coffee, Gold tier) has a delivery promise of 2026-05-30 — what "
    "do we need to think about and what do we tell them?"
)


@dataclass
class PersonaRun:
    persona: str
    role_label: str
    final_response: str = ""
    tool_calls: list[str] = field(default_factory=list)
    duration_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    safety_findings: list[dict] = field(default_factory=list)


def run_persona(persona: str) -> PersonaRun:
    session = AgentSession(persona=persona)
    started = time.time()
    final_text = ""
    tool_calls: list[str] = []
    safety: list[dict] = []

    for event in session.stream_turn(PROMPT):
        if event["type"] == "tool_call":
            tool_calls.append(event["name"])
        elif event["type"] == "safety":
            safety = event["findings"]
        elif event["type"] == "final":
            final_text = event["text"]

    duration_ms = int((time.time() - started) * 1000)

    # Pull token usage from the latest log line.
    input_tokens = output_tokens = None
    if session.logger.path.exists():
        last = session.logger.path.read_text(encoding="utf-8").strip().split("\n")[-1]
        rec = json.loads(last)
        input_tokens = rec.get("input_tokens")
        output_tokens = rec.get("output_tokens")

    return PersonaRun(
        persona=persona,
        role_label=PERSONAS[persona].role_label,
        final_response=final_text,
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        safety_findings=safety,
    )


def render_md(runs: list[PersonaRun]) -> str:
    md: list[str] = ["# Phase 7 — Persona comparison\n\n"]
    md.append(
        "Same prompt, three personas. Notice how each persona reframes the "
        "same underlying shipment data toward its role's priorities.\n\n"
    )
    md.append(f"**Prompt:**\n```\n{PROMPT.strip()}\n```\n\n")
    md.append("## Summary\n\n")
    md.append("| Persona | Role | Tools | In tok | Out tok | Latency |\n")
    md.append("|---|---|---|---|---|---|\n")
    for r in runs:
        tools = ", ".join(r.tool_calls) or "—"
        md.append(
            f"| `{r.persona}` | {r.role_label} | {tools} "
            f"| {r.input_tokens or '–'} | {r.output_tokens or '–'} "
            f"| {r.duration_ms / 1000:.1f}s |\n"
        )
    md.append("\n")
    for r in runs:
        md.append(f"## `{r.persona}` — {r.role_label}\n\n")
        md.append("```\n" + r.final_response.strip() + "\n```\n\n")
    return "".join(md)


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    runs: list[PersonaRun] = []
    for persona_name in ("ops_associate", "finance_partner", "customer_lead"):
        print(f"\n=== {persona_name} ===")
        r = run_persona(persona_name)
        print(f"  tools: {r.tool_calls}")
        print(
            f"  duration={r.duration_ms}ms  in_tok={r.input_tokens}  out_tok={r.output_tokens}"
        )
        runs.append(r)

    md_path = out_dir / "phase7-persona-compare.md"
    json_path = out_dir / "phase7-persona-compare.json"
    md_path.write_text(render_md(runs), encoding="utf-8")
    json_path.write_text(
        json.dumps([asdict(r) for r in runs], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nDone.\n  md:   {md_path}\n  json: {json_path}")


if __name__ == "__main__":
    main()
