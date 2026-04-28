"""Phase 9 — Multi-seed acceptance suite.

Runs the same AT-1..AT-5 + ADV-1..ADV-6 prompts N times each (default N=3),
records per-run pass/fail, and reports pass-rate distributions.

Why: Phase 5 discovered that Anthropic's Claude is NOT deterministic at
temperature=0 (server-side variance). Single-run pass/fail gives misleading
signal — we should report distributions ("8 of 9 attempts passed AT-3" =
89% pass rate) rather than binary outcomes.

Output:
  docs/phase9-multi-seed-results.json  — raw per-attempt records
  docs/phase9-multi-seed-results.md    — human-readable distributions

Usage:
  PYTHONPATH=src python eval/run_multi_seed.py             # default N=3
  PYTHONPATH=src python eval/run_multi_seed.py --seeds 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Reuse the Phase 5 runner for the per-case scoring logic.
from run_acceptance_tests import (  # type: ignore[import-not-found]
    CaseRun,
    run_one,
    score_case,
)

_REPO = Path(__file__).resolve().parents[1]
_EVAL = _REPO / "eval"
_OUT = _REPO / "docs"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seeds",
        type=int,
        default=3,
        help="Number of attempts per case. Default 3 (=> 33 LLM calls total).",
    )
    args = parser.parse_args()

    cases = yaml.safe_load((_EVAL / "acceptance_tests.yaml").read_text())["cases"]
    probes = yaml.safe_load((_EVAL / "adversarial_probes.yaml").read_text())["probes"]
    specs = [
        ("acceptance", c["id"], c["title"], c["prompt"], c["checks"]) for c in cases
    ] + [
        ("adversarial", p["id"], p["title"], p["prompt"], p["checks"]) for p in probes
    ]

    started = time.time()
    results: list[dict] = []
    for seed in range(1, args.seeds + 1):
        for kind, case_id, title, prompt, checks in specs:
            label = f"{case_id} [seed {seed}/{args.seeds}]"
            print(f"\n=== {label} ({kind}) ===")
            run = run_one(case_id, title, prompt)
            score_case(run, checks)
            verdict = "✅" if run.passed else "❌"
            print(f"  {verdict} {sum(c.passed for c in run.checks)}/{len(run.checks)} checks pass")
            results.append({"seed": seed, "kind": kind, **asdict(run)})

    duration = int(time.time() - started)

    # Aggregate pass-rate per case
    by_case: dict[str, list[dict]] = {}
    for r in results:
        by_case.setdefault(r["case_id"], []).append(r)

    summary = []
    for case_id, runs in by_case.items():
        n = len(runs)
        passed = sum(1 for r in runs if all(c["passed"] for c in r["checks"]))
        avg_dur = sum(r["duration_ms"] for r in runs) / n
        avg_in = sum((r["input_tokens"] or 0) for r in runs) / n
        avg_out = sum((r["output_tokens"] or 0) for r in runs) / n
        # Per-check pass rate: which checks are flaky?
        check_stats: dict[str, dict[str, int]] = {}
        for r in runs:
            for c in r["checks"]:
                s = check_stats.setdefault(c["name"], {"passed": 0, "total": 0})
                s["passed"] += int(c["passed"])
                s["total"] += 1
        summary.append(
            {
                "case_id": case_id,
                "kind": runs[0]["kind"],
                "title": runs[0]["title"],
                "n_attempts": n,
                "n_passed": passed,
                "pass_rate": passed / n,
                "avg_duration_ms": avg_dur,
                "avg_input_tokens": avg_in,
                "avg_output_tokens": avg_out,
                "check_pass_rates": check_stats,
            }
        )

    # Write outputs
    raw_path = _OUT / "phase9-multi-seed-results.json"
    raw_path.write_text(
        json.dumps(
            {"summary": summary, "raw_runs": results, "elapsed_s": duration},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    md = ["# Phase 9 — Multi-seed acceptance results\n\n"]
    md.append(
        f"Each acceptance case + adversarial probe was run **{args.seeds} times** "
        f"on identical inputs. Total: {len(results)} LLM calls in "
        f"{duration // 60}m {duration % 60}s.\n\n"
    )
    md.append("## Pass-rate distribution per case\n\n")
    md.append("| Case | Kind | Pass rate | Avg latency | Avg in tok | Avg out tok |\n")
    md.append("|---|---|---|---|---|---|\n")
    for s in summary:
        rate_pct = s["pass_rate"] * 100
        rate_str = (
            f"✅ **{s['n_passed']}/{s['n_attempts']}** ({rate_pct:.0f}%)"
            if rate_pct == 100
            else f"⚠ {s['n_passed']}/{s['n_attempts']} ({rate_pct:.0f}%)"
            if rate_pct >= 67
            else f"❌ {s['n_passed']}/{s['n_attempts']} ({rate_pct:.0f}%)"
        )
        md.append(
            f"| `{s['case_id']}` | {s['kind']} | {rate_str} "
            f"| {s['avg_duration_ms'] / 1000:.1f}s "
            f"| {s['avg_input_tokens']:.0f} | {s['avg_output_tokens']:.0f} |\n"
        )

    md.append("\n## Per-check flakiness\n\n")
    md.append(
        "Checks that pass on every seed = robust. Checks that pass on some seeds "
        "but fail on others = sensitive to temp=0 non-determinism.\n\n"
    )
    for s in summary:
        any_flaky = any(
            stats["passed"] != stats["total"]
            for stats in s["check_pass_rates"].values()
        )
        if not any_flaky:
            continue
        md.append(f"### `{s['case_id']}`\n\n")
        for check_name, stats in s["check_pass_rates"].items():
            badge = "✅" if stats["passed"] == stats["total"] else "⚠"
            md.append(
                f"- {badge} `{check_name}`: {stats['passed']}/{stats['total']}\n"
            )
        md.append("\n")

    (_OUT / "phase9-multi-seed-results.md").write_text("".join(md), encoding="utf-8")

    overall_pass = sum(s["n_passed"] for s in summary)
    overall_total = sum(s["n_attempts"] for s in summary)
    print(f"\n{'=' * 64}")
    print(
        f"Overall: {overall_pass}/{overall_total} "
        f"({overall_pass / overall_total * 100:.1f}%) "
        f"in {duration // 60}m{duration % 60}s"
    )
    print(f"  raw:    {raw_path}")
    print(f"  report: {_OUT / 'phase9-multi-seed-results.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
