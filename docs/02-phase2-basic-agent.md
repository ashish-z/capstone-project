# Phase 2 — Basic Working Agent

**Goal:** Stand up the smallest end-to-end agent that satisfies the rubric: Python + LLM + ≥1 tool + printable I/O + documentation. Everything in this phase is replaceable by Phase 3 onwards; the point is to *prove the loop works*.

## What we built

```
┌──────────────┐    user prompt    ┌────────────────┐  tool_call    ┌────────────────────┐
│  CLI loop    │ ────────────────▶ │  ReAct agent   │ ────────────▶ │ lookup_shipment    │
│ (__main__)   │ ◀──────────────── │  (LangGraph)   │ ◀──────────── │  (reads JSON       │
└──────────────┘   final answer    │  Haiku 4.5     │  tool_result  │   fixtures)        │
                                   └────────────────┘                └────────────────────┘
```

| Component | File | Notes |
|---|---|---|
| LLM | `langchain_anthropic.ChatAnthropic` | `claude-haiku-4-5-20251001`, temp=0 |
| Agent runtime | `langgraph.prebuilt.create_react_agent` | Canonical ReAct graph |
| System prompt | [`src/freight_copilot/prompts/system.py`](../src/freight_copilot/prompts/system.py) | Safety rails baked in (no commits, no invented facts) |
| Tool | [`src/freight_copilot/tools/shipment_lookup.py`](../src/freight_copilot/tools/shipment_lookup.py) | Reads `data/shipments/{id}.json` |
| Fixtures | `data/shipments/FRT-104{2,3,4,5,6}.json` | One per AT-1..AT-5 |
| CLI | [`src/freight_copilot/__main__.py`](../src/freight_copilot/__main__.py) | Single-shot loop (multi-turn arrives in Phase 3) |
| Tests | [`tests/test_shipment_lookup.py`](../tests/test_shipment_lookup.py) | 7 passing |

## Key design decisions

| Decision | Why |
|---|---|
| **LangGraph `create_react_agent`** instead of hand-rolled loop | Less code, well-tested ReAct routing, same primitive we extend in Phase 3+ for memory and additional tools |
| **JSON fixtures** as the "shipment system" | We don't have a real TMS API to call; fixtures let us exercise the full agent loop end-to-end while keeping every fact verifiable |
| **Safety rails in the system prompt** (not yet in code) | Phase 2 only needs the agent to *behave* safely. Tool-level enforcement (read-only-only, refusal hooks) lands in Phase 5 |
| **Temperature 0** | Deterministic eval runs; we don't want creativity in operations decisions |
| **Per-tool docstring is the schema** | LangChain's `@tool` decorator turns the docstring into the tool spec. The docstring tells the LLM *when* to call and *what to expect* |

## How to run

```bash
# 1) Activate venv
source .venv/bin/activate

# 2) Make sure .env has ANTHROPIC_API_KEY set (copy from .env.example)
cp .env.example .env  # then edit

# 3) Run the CLI
PYTHONPATH=src python -m freight_copilot
```

Then type something like:

```
> Triage shipment FRT-1042 for me. What's wrong and what should I do next?
```

## Tests

```bash
PYTHONPATH=src pytest tests/ -v
```

Phase 2 ships 7 tests covering the tool's happy path, all 5 fixtures, full-payload shape, and unknown-ID handling.

## Cost expectation

| Run type | Tokens (in/out) | Cost @ Haiku 4.5 |
|---|---|---|
| Single triage of one shipment | ~3,500 in / ~500 out | ~$0.006 |
| Full AT-1..AT-5 sweep | ~17k in / ~2.5k out | ~$0.03 |

So Phase 2 development + experimentation is comfortably under $0.50 even with heavy iteration.

## Sample run — AT-1 (customs hold)

Captured live output of the agent on AT-1 is in [phase2-at1-sample-run.txt](phase2-at1-sample-run.txt). Highlights:

- ✅ Tool invoked (`lookup_shipment("FRT-1042")`)
- ✅ Diagnosis correctly identified missing Commercial Invoice as root cause
- ✅ All key facts cited from fixture data (vessel, customer tier, SLA breach date, demurrage rate)
- ✅ 3 ranked recommendations with resolution times and risk levels
- ✅ Customer email draft used hedged language ("we expect", "should the hold extend")
- ✅ Safety rail held — agent appended **"Do not send this email yet"** unprompted

Phase 5 will replay all 5 acceptance test cases (AT-1..AT-5) with adversarial probes.

## What this phase deliberately does NOT do (and which phase fixes it)

| Gap | Filled by |
|---|---|
| No multi-turn memory — every prompt is fresh | Phase 3 |
| No SOPs / RAG retrieval — agent only knows what `lookup_shipment` returns | Phase 4 |
| No safety enforcement at the tool layer (only soft via prompt) | Phase 5 |
| No long-term memory of customer/shipment history across sessions | Phase 6 |
| No role/tone adaptation | Phase 7 |
| No web UI | Phase 8 |
| No formal evaluation harness | Phase 9 |
