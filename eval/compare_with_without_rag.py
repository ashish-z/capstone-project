"""Phase 4 ablation — run AT-1..AT-5 with and without the SOP RAG tool.

Saves both transcripts side-by-side so the Phase 4 doc can compare:
- SOP citation rate
- Procedural correctness (escalation thresholds, customer-tier rules)
- Length / token cost
- Whether the safety rail still holds in the no-RAG variant
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Make the freight_copilot package importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from freight_copilot.agent import AgentSession  # noqa: E402

PROMPTS = [
    (
        "AT-1",
        "Triage shipment FRT-1042. We have a customs hold — what's our policy and what should I do next?",
    ),
    (
        "AT-2",
        "Triage shipment FRT-1043. The Houston port is closed — what's our SOP for weather events?",
    ),
    (
        "AT-3",
        "Triage shipment FRT-1044. We got rolled by MSC. What does our SOP say about when to re-book vs. accept?",
    ),
    (
        "AT-4",
        "Triage shipment FRT-1045. ETA slipped, no carrier update. When should I escalate to senior ops?",
    ),
    (
        "AT-5",
        "Triage shipment FRT-1046. HBL/MBL consignee mismatch. What severity is this and what's the resolution path?",
    ),
]


@dataclass
class CaseResult:
    case_id: str
    use_rag: bool
    final_response: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    duration_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None


def run_case(case_id: str, prompt: str, use_rag: bool) -> CaseResult:
    session = AgentSession(use_rag=use_rag)
    started = time.time()
    final_text = ""
    tool_calls: list[dict] = []

    for event in session.stream_turn(prompt):
        if event["type"] == "tool_call":
            tool_calls.append({"name": event["name"], "args": event["args"]})
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

    return CaseResult(
        case_id=case_id,
        use_rag=use_rag,
        final_response=final_text,
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    all_results: list[CaseResult] = []

    for case_id, prompt in PROMPTS:
        for use_rag in (False, True):
            label = "rag" if use_rag else "norag"
            print(f"\n=== {case_id} / {label} ===")
            print(f"PROMPT: {prompt}")
            res = run_case(case_id, prompt, use_rag)
            all_results.append(res)
            print(f"  tools used: {[t['name'] for t in res.tool_calls]}")
            print(
                f"  duration: {res.duration_ms}ms  "
                f"in_tok: {res.input_tokens}  out_tok: {res.output_tokens}"
            )

    raw = out_dir / "phase4-comparison-raw.json"
    raw.write_text(
        json.dumps([asdict(r) for r in all_results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Build a markdown side-by-side report
    md = ["# Phase 4 — RAG ablation results\n"]
    md.append("Each case was run twice on identical inputs: once with the\n")
    md.append("`search_sops` tool available (RAG ON), once without (RAG OFF).\n")
    md.append("\n## Summary\n")
    md.append(
        "| Case | Mode | Tools used | SOPs cited | In tok | Out tok | Latency (s) |\n"
    )
    md.append("|---|---|---|---|---|---|---|\n")
    for res in all_results:
        tool_names = ", ".join(t["name"] for t in res.tool_calls) or "—"
        sops_cited = len(_citations_in(res.final_response))
        md.append(
            f"| {res.case_id} | {'RAG' if res.use_rag else 'no-RAG'} "
            f"| {tool_names} | {sops_cited} "
            f"| {res.input_tokens or '–'} | {res.output_tokens or '–'} "
            f"| {res.duration_ms / 1000:.1f} |\n"
        )

    md.append("\n## Per-case transcripts\n")
    for case_id, _prompt in PROMPTS:
        md.append(f"\n### {case_id}\n")
        norag = next(r for r in all_results if r.case_id == case_id and not r.use_rag)
        rag = next(r for r in all_results if r.case_id == case_id and r.use_rag)
        md.append("\n#### no-RAG\n")
        md.append(f"Tools: {[t['name'] for t in norag.tool_calls]}\n\n")
        md.append("```\n" + norag.final_response.strip() + "\n```\n")
        md.append("\n#### RAG\n")
        md.append(f"Tools: {[t['name'] for t in rag.tool_calls]}\n\n")
        md.append("```\n" + rag.final_response.strip() + "\n```\n")

    out_md = out_dir / "phase4-comparison.md"
    out_md.write_text("".join(md), encoding="utf-8")
    print(f"\nDone.\n  raw: {raw}\n  report: {out_md}")


def _citations_in(text: str) -> list[str]:
    """Best-effort: SOP filename mentions in the response (e.g., 'sop-customs-...md')."""
    import re

    return re.findall(r"sop-[a-z0-9-]+\.md", text)


if __name__ == "__main__":
    main(Path(__file__).resolve().parents[1] / "docs")
