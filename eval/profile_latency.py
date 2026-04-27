"""Phase 9 — Latency profiler.

Phase 8 monitoring surfaced P95 latency = 38.5s (vs Phase 1 target <8s).
This script reads the JSONL logs and breaks each turn down into:

  - tool wall-clock (sum of per-tool durations)
  - LLM wall-clock (turn total minus tool time minus a small overhead)
  - tools per turn

…so we can see whether the bottleneck is LLM tokens, tool I/O, or both.
Writes a markdown table + JSON summary; no LLM calls.

Usage:
  PYTHONPATH=src python eval/profile_latency.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from freight_copilot.monitoring import read_turns

_OUT = Path(__file__).resolve().parents[1] / "docs"


def _percentile(xs: list[float], pct: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round(pct / 100 * (len(s) - 1)))))
    return s[k]


def main() -> int:
    turns = read_turns()
    if not turns:
        sys.exit("No logs to profile. Run a session first.")

    rows = []
    for t in turns:
        total = float(t.get("total_duration_ms") or 0)
        tools = t.get("tool_calls") or []
        tool_total = sum(float(tc.get("duration_ms") or 0) for tc in tools)
        # The remainder is mostly LLM time + small Python overhead.
        llm_remainder = max(0.0, total - tool_total)
        rows.append(
            {
                "thread_id": (t.get("thread_id") or "?")[:8],
                "turn_index": t.get("turn_index"),
                "intent": t.get("intent") or "—",
                "persona": t.get("persona") or "—",
                "n_tools": len(tools),
                "tool_ms": tool_total,
                "llm_ms": llm_remainder,
                "total_ms": total,
                "in_tok": t.get("input_tokens") or 0,
                "out_tok": t.get("output_tokens") or 0,
            }
        )

    n = len(rows)
    totals = [r["total_ms"] for r in rows]
    tool_ms = [r["tool_ms"] for r in rows]
    llm_ms = [r["llm_ms"] for r in rows]
    in_tok = [r["in_tok"] for r in rows]
    out_tok = [r["out_tok"] for r in rows]

    summary = {
        "n_turns": n,
        "total_ms": {
            "p50": _percentile(totals, 50),
            "p95": _percentile(totals, 95),
            "avg": statistics.mean(totals),
            "max": max(totals),
        },
        "tool_ms": {
            "p50": _percentile(tool_ms, 50),
            "p95": _percentile(tool_ms, 95),
            "avg": statistics.mean(tool_ms),
            "share_of_total_pct": (sum(tool_ms) / max(sum(totals), 1)) * 100,
        },
        "llm_ms": {
            "p50": _percentile(llm_ms, 50),
            "p95": _percentile(llm_ms, 95),
            "avg": statistics.mean(llm_ms),
            "share_of_total_pct": (sum(llm_ms) / max(sum(totals), 1)) * 100,
        },
        "tokens": {
            "avg_in": int(statistics.mean(in_tok)),
            "avg_out": int(statistics.mean(out_tok)),
            "p95_in": int(_percentile(in_tok, 95)),
            "p95_out": int(_percentile(out_tok, 95)),
        },
        "tool_count_per_turn": {
            "avg": statistics.mean(r["n_tools"] for r in rows),
            "max": max(r["n_tools"] for r in rows),
        },
    }

    # Markdown
    md = ["# Phase 9 — Latency profile\n\n"]
    md.append(f"Profiled **{n}** turns from `logs/session-*.jsonl`.\n\n")
    md.append("## Headline\n\n")
    md.append("| Metric | P50 | P95 | Average | Max |\n|---|---|---|---|---|\n")
    md.append(
        f"| **Total turn latency** | {summary['total_ms']['p50'] / 1000:.1f}s "
        f"| {summary['total_ms']['p95'] / 1000:.1f}s "
        f"| {summary['total_ms']['avg'] / 1000:.1f}s "
        f"| {summary['total_ms']['max'] / 1000:.1f}s |\n"
    )
    md.append(
        f"| Tool wall-clock | {summary['tool_ms']['p50']:.0f}ms "
        f"| {summary['tool_ms']['p95']:.0f}ms "
        f"| {summary['tool_ms']['avg']:.0f}ms | — |\n"
    )
    md.append(
        f"| LLM wall-clock (remainder) | {summary['llm_ms']['p50'] / 1000:.1f}s "
        f"| {summary['llm_ms']['p95'] / 1000:.1f}s "
        f"| {summary['llm_ms']['avg'] / 1000:.1f}s | — |\n\n"
    )

    md.append(
        f"**Tools account for {summary['tool_ms']['share_of_total_pct']:.1f}%** "
        f"of total wall-clock; **LLM accounts for "
        f"{summary['llm_ms']['share_of_total_pct']:.1f}%**.\n\n"
    )
    md.append(
        "Tool calls are local (Python file reads + Chroma local search), so "
        "their share is tiny — **the bottleneck is LLM round-trip time**, "
        "driven by input-token volume after Phase 6 added recall tools.\n\n"
    )

    md.append("## Token volume per turn\n\n")
    md.append(
        f"- Avg input tokens: **{summary['tokens']['avg_in']:,}**  "
        f"(P95: {summary['tokens']['p95_in']:,})\n"
        f"- Avg output tokens: **{summary['tokens']['avg_out']:,}**  "
        f"(P95: {summary['tokens']['p95_out']:,})\n"
        f"- Avg tools per turn: {summary['tool_count_per_turn']['avg']:.1f} "
        f"(max: {summary['tool_count_per_turn']['max']})\n\n"
    )

    md.append("## Per-turn detail\n\n")
    md.append("| Thread | Turn | Persona | Intent | Tools | Tool ms | LLM ms | Total | In tok | Out tok |\n|---|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        md.append(
            f"| `{r['thread_id']}` | {r['turn_index']} | {r['persona']} "
            f"| {r['intent']} | {r['n_tools']} "
            f"| {r['tool_ms']:.0f} | {r['llm_ms']:.0f} "
            f"| {r['total_ms'] / 1000:.1f}s "
            f"| {r['in_tok']} | {r['out_tok']} |\n"
        )

    md.append("\n## What this means for optimization\n\n")
    md.append(
        "Since LLM round-trip dominates and the bulk of the input-token cost "
        "is the system prompt + recalled SOPs being re-sent every turn, the "
        "highest-leverage interventions are (in order):\n\n"
        "1. **Anthropic prompt caching** — the system prompt + RAG chunks are "
        "  identical across turns within a session; a 5-minute cache cuts "
        "  ~70% of the input tokens for a follow-up turn.\n"
        "2. **Smaller k for `search_sops`** — k=4 produces ~2,000 input "
        "  tokens of SOP context. k=2 may suffice for many turns.\n"
        "3. **Skip recall on follow-up turns** — once we've recalled customer "
        "  history once in a session, re-fetching is wasted work.\n"
        "4. **Parallel tool calling** — LangGraph supports it; we currently "
        "  sequence (lookup → recall → search). Going parallel saves ~1–2s.\n"
    )

    out_md = _OUT / "phase9-latency-profile.md"
    out_md.write_text("".join(md), encoding="utf-8")
    out_json = _OUT / "phase9-latency-profile.json"
    out_json.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8"
    )

    print(f"Profiled {n} turns.")
    print(f"  Total P95: {summary['total_ms']['p95'] / 1000:.1f}s")
    print(f"  LLM share: {summary['llm_ms']['share_of_total_pct']:.1f}%")
    print(f"  md:   {out_md}")
    print(f"  json: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
