"""Phase 9 — RAGAs evaluation on AT-1..AT-5 acceptance cases.

For each acceptance case we already have:
  - prompt (the question)
  - final_response (the answer)
  - tool_calls / search_sops results (the retrieved context)

RAGAs metrics we score:
  - faithfulness         : Does the answer's claims trace to the retrieved context?
  - answer_relevancy     : Does the answer actually address the question?
  - context_precision    : Are the retrieved chunks relevant (signal vs noise)?

Reads from `docs/phase9-multi-seed-results.json` (or phase5-acceptance-results.json
as fallback). Picks the seed-1 run for each AT case.

Writes:
  docs/phase9-ragas-results.json
  docs/phase9-ragas-results.md

Usage:
  PYTHONPATH=src python eval/run_ragas.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

load_dotenv(override=True)

_REPO = Path(__file__).resolve().parents[1]
_OUT = _REPO / "docs"


def _retrieve_chunks_for_case(prompt: str, k: int = 4) -> list[str]:
    """Re-issue a SOP retrieval for the prompt to get the full chunks.

    The session log's `result_preview` is truncated at 300 chars by design
    (Phase 3 SessionLogger). RAGAs needs the full chunk text to score
    context-precision and faithfulness, so we re-run the deterministic
    semantic search directly.
    """
    from freight_copilot.retrieval.store import search

    results = search(prompt, k=k)
    return [r["text"] for r in results if r.get("text")]


def _build_dataset(source: Path) -> Dataset:
    payload = json.loads(source.read_text())
    rows: list[dict] = []

    # Phase 9 multi-seed shape
    if "raw_runs" in payload:
        for r in payload["raw_runs"]:
            if r.get("kind") != "acceptance" or r.get("seed") != 1:
                continue
            chunks = _retrieve_chunks_for_case(r["prompt"])
            rows.append(
                {
                    "case_id": r["case_id"],
                    "user_input": r["prompt"].strip(),
                    "response": r["final_response"],
                    "retrieved_contexts": chunks or ["(no SOP context retrieved)"],
                }
            )
    elif "acceptance_cases" in payload:
        for r in payload["acceptance_cases"]:
            chunks = _retrieve_chunks_for_case(r["prompt"])
            rows.append(
                {
                    "case_id": r["case_id"],
                    "user_input": r["prompt"].strip(),
                    "response": r["final_response"],
                    "retrieved_contexts": chunks or ["(no SOP context retrieved)"],
                }
            )
    else:
        sys.exit(f"Unrecognized source shape: {source}")

    if not rows:
        sys.exit(f"No acceptance-case records in {source}")

    print(f"Built RAGAs dataset of {len(rows)} cases.")
    return Dataset.from_list(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=None)
    args = parser.parse_args()

    src = args.source or (_OUT / "phase9-multi-seed-results.json")
    if not src.exists():
        src = _OUT / "phase5-acceptance-results.json"
    if not src.exists():
        sys.exit(f"No source file found at either docs/phase9-* or docs/phase5-*")

    ds = _build_dataset(src)

    # RAGAs uses an LLM judge for each metric. We use Sonnet 4.6 for stronger
    # judgment than the Haiku-4.5 the agent itself uses.
    judge_model = os.getenv("JUDGE_MODEL", "claude-sonnet-4-6")
    print(f"Using judge model: {judge_model}")
    # max_tokens=4096 — RAGAs faithfulness extracts every claim from the
    # response, which can run long for our multi-section triage answers.
    judge_llm = ChatAnthropic(model=judge_model, temperature=0, max_tokens=4096)

    # Import RAGAs lazily — heavy dependency.
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
    from ragas.metrics import (
        Faithfulness,
        ResponseRelevancy,
        # ContextPrecision needs a reference answer; we don't have one, so
        # we use ContextPrecisionWithoutReference instead.
        LLMContextPrecisionWithoutReference,
    )
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    # Use sentence-transformers via LangChain's HuggingFace wrapper, then wrap
    # that with RAGAs' LangchainEmbeddingsWrapper.
    from langchain_community.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings

    raw_embeddings = LCHuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    embeddings = LangchainEmbeddingsWrapper(raw_embeddings)
    judge = LangchainLLMWrapper(judge_llm)

    samples: list[SingleTurnSample] = []
    for row in ds:
        samples.append(
            SingleTurnSample(
                user_input=row["user_input"],
                response=row["response"],
                retrieved_contexts=row["retrieved_contexts"],
            )
        )
    eval_ds = EvaluationDataset(samples=samples)

    metrics = [
        Faithfulness(llm=judge),
        ResponseRelevancy(llm=judge, embeddings=embeddings),
        LLMContextPrecisionWithoutReference(llm=judge),
    ]

    print("Running RAGAs (this calls the judge LLM per metric per row)…")
    result = evaluate(eval_ds, metrics=metrics, llm=judge, embeddings=embeddings)

    # Convert to a per-case dict
    df = result.to_pandas()
    df["case_id"] = [r["case_id"] for r in ds]
    rows_out = df.to_dict(orient="records")

    # Aggregate
    metric_cols = [c for c in df.columns if c not in ("case_id", "user_input", "response", "retrieved_contexts")]
    summary: dict[str, dict[str, float]] = {}
    for m in metric_cols:
        vals = [v for v in df[m].tolist() if v is not None and not (v != v)]  # drop NaN
        if not vals:
            continue
        summary[m] = {
            "min": float(min(vals)),
            "max": float(max(vals)),
            "mean": float(sum(vals) / len(vals)),
            "n": len(vals),
        }

    out = {
        "judge_model": judge_model,
        "n_cases": len(rows_out),
        "summary_by_metric": summary,
        "per_case": rows_out,
    }
    (_OUT / "phase9-ragas-results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )

    md = ["# Phase 9 — RAGAs evaluation\n\n"]
    md.append(
        f"Judge model: **{judge_model}**  ·  cases scored: **{len(rows_out)}**\n\n"
    )
    md.append("## Summary by metric\n\n")
    md.append("| Metric | Mean | Min | Max | n |\n|---|---|---|---|---|\n")
    target = {
        "faithfulness": 0.85,
        "answer_relevancy": 0.85,
        "llm_context_precision_without_reference": 0.80,
    }
    for m in metric_cols:
        if m not in summary:
            continue
        s = summary[m]
        t = target.get(m)
        badge = ""
        if t is not None:
            badge = " ✅" if s["mean"] >= t else " ❌"
        target_str = f" (target: ≥{t})" if t else ""
        md.append(
            f"| `{m}` | **{s['mean']:.3f}**{badge}{target_str} | "
            f"{s['min']:.3f} | {s['max']:.3f} | {s['n']} |\n"
        )

    md.append("\n## Per-case scores\n\n")
    md.append("| Case | " + " | ".join(metric_cols) + " |\n|---|" + "---|" * len(metric_cols) + "\n")
    for row in rows_out:
        cells = [f"`{row['case_id']}`"]
        for m in metric_cols:
            v = row.get(m)
            cells.append(f"{v:.3f}" if isinstance(v, (int, float)) else "—")
        md.append("| " + " | ".join(cells) + " |\n")

    (_OUT / "phase9-ragas-results.md").write_text("".join(md), encoding="utf-8")

    print("\nDone.")
    print(f"  json: {_OUT / 'phase9-ragas-results.json'}")
    print(f"  md:   {_OUT / 'phase9-ragas-results.md'}")
    print("\nSummary:")
    for m, s in summary.items():
        print(f"  {m:50s} mean={s['mean']:.3f}  (n={s['n']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
