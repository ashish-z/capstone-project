# Phase 4 — Knowledge & Retrieval (RAG)

**Goal:** Move from "the agent reasons from prompt-instilled defaults" to "the agent retrieves the team's actual SOPs and cites them by filename." Phase 4 is the difference between a confident-sounding generalist and a citable, auditable specialist.

## What's new vs. Phase 3

| Capability | Phase 3 | Phase 4 |
|---|---|---|
| Tools | `lookup_shipment`, `carrier_history`, `external_events` | + `search_sops` (semantic search over SOP corpus) |
| Knowledge source | Whatever ends up in the system prompt | SOP markdown files indexed in ChromaDB |
| Citations | Implicit (data sources) | Explicit (SOP filename + section) |
| Grounding for policy claims ("we escalate after 4h") | Prompt-instilled, possibly hallucinated | Retrieved + cited |

## Architecture

```
                            ┌──────────────────────────────┐
                            │  data/sops/*.md (9 files)    │
                            └──────────────┬───────────────┘
                                           │ ingest.py
                                           │ (chunk 800 / overlap 150,
                                           │  markdown-aware splitter)
                                           ▼
┌────────────┐                   ┌────────────────────────────────┐
│  CLI       │                   │  ChromaDB (chroma_db/)         │
└────┬───────┘                   │  embedding_fn = MiniLM-L6-v2   │
     │                           │  73 chunks, cosine distance    │
     ▼                           └─────────────┬──────────────────┘
┌─────────────────────────────────────────┐    │
│  AgentSession (LangGraph + MemorySaver) │    │
│                                         │    │
│  ┌──────────────────────────────────┐   │    │
│  │  Claude Haiku 4.5 (ReAct)        │   │    │
│  └──────────────┬───────────────────┘   │    │
│                 │                       │    │
│   ┌─────────────┼─────────────────────┐ │    │
│   ▼             ▼                     ▼ │    │
│ data tools   carrier_history   search_sops──┘
│ lookup_      external_events   (k=4 chunks
│ shipment                        + source +
│                                 distance)
└─────────────────────────────────────────┘
```

## SOP corpus (9 documents, 73 chunks total)

| File | Coverage | Chunks |
|---|---|---|
| `sop-customs-hold-missing-ci.md` | AT-1 | 7 |
| `sop-weather-port-closure.md` | AT-2 | 7 |
| `sop-capacity-rollover.md` | AT-3 | 9 |
| `sop-silent-eta-slippage.md` | AT-4 | 9 |
| `sop-doc-discrepancy-hbl-mbl.md` | AT-5 | 9 |
| `sop-customer-tier-comms.md` | Tier SLAs / tone (cross-cutting) | 7 |
| `sop-demurrage-management.md` | Cost recovery (cross-cutting) | 9 |
| `sop-escalation-handoff.md` | Escalation triggers (cross-cutting) | 7 |
| `sop-customer-comm-style-guide.md` | Drafting rules (cross-cutting) | 9 |

Re-ingest:
```bash
PYTHONPATH=src python -m freight_copilot.retrieval.ingest
```

## Retrieval health check

Standalone retrieval calls (independent of the agent) — top-2 hits per canonical query:

| Query | Top hit | Distance | Top-2 hit |
|---|---|---|---|
| `missing commercial invoice customs hold` | `sop-customs-hold-missing-ci.md` | 0.218 | `sop-customs-hold-missing-ci.md` |
| `Gold tier customer SLA acknowledgment window` | `sop-capacity-rollover.md`* | 0.358 | `sop-customer-tier-comms.md` |
| `silent ETA slippage escalate to senior ops` | `sop-silent-eta-slippage.md` | 0.396 | `sop-escalation-handoff.md` |
| `demurrage waiver request` | `sop-demurrage-management.md` | 0.318 | `sop-doc-discrepancy-hbl-mbl.md` |
| `HBL MBL consignee mismatch entity suffix` | `sop-doc-discrepancy-hbl-mbl.md` | 0.424 | `sop-doc-discrepancy-hbl-mbl.md` |

*The Gold-tier query is the one weak spot — the rollover SOP's escalation table also references "Gold tier", which competes with the dedicated tier-comms SOP. Both surface in top-2, so the agent (k=4) gets both. Test suite asserts top-4 routing accordingly.

## Ablation — RAG vs no-RAG on AT-1..AT-5

The `eval/compare_with_without_rag.py` harness runs each acceptance test case twice on identical inputs: once with `search_sops` available, once without. Same model (Haiku 4.5), same prompt, same temperature (0).

### Summary

| Case | Mode | Tools used | SOPs cited | In tok | Out tok | Latency (s) |
|---|---|---|---|---|---|---|
| AT-1 | no-RAG | `lookup_shipment`, `external_events` | **0** | 3,560 | 1,648 | 22.1 |
| AT-1 | **RAG** | `lookup_shipment`, `search_sops` | **5** | 5,461 | 1,442 | 31.1 |
| AT-2 | no-RAG | `lookup_shipment`, `external_events`, `lookup_shipment` | **0** | 4,590 | 1,331 | 18.3 |
| AT-2 | **RAG** | `lookup_shipment`, `external_events`, `search_sops` | **4** | 5,050 | 1,304 | 15.7 |
| AT-3 | no-RAG | `lookup_shipment`, `carrier_history` | **1 (FABRICATED)** | 3,837 | 1,516 | 19.6 |
| AT-3 | **RAG** | `lookup_shipment`, `search_sops` | **4** | 5,348 | 1,814 | 20.4 |
| AT-4 | no-RAG | `lookup_shipment`, `external_events`, `carrier_history` | **0** | 3,680 | 1,683 | 23.0 |
| AT-4 | **RAG** | `lookup_shipment`, `search_sops`, `external_events`, `carrier_history`, `search_sops` | **7** | 5,973 | 1,454 | 27.9 |
| AT-5 | no-RAG | `lookup_shipment`, `external_events` | **0** | 3,637 | 1,762 | 21.9 |
| AT-5 | **RAG** | `lookup_shipment`, `search_sops` | **3** | 5,006 | 1,306 | 16.5 |

### Aggregates

|  | no-RAG | RAG | Delta |
|---|---|---|---|
| Avg input tokens | 3,861 | 5,368 | **+39%** (the SOP chunks add cost) |
| Avg output tokens | 1,588 | 1,464 | **−8%** (RAG answers are tighter; less padding) |
| Avg total tokens | 5,449 | 6,832 | +25% |
| Avg latency | 21.0 s | 22.3 s | +6% (Chroma is local, basically free) |
| **SOPs correctly cited** | **0.2** / case | **4.6** / case | **+23×** |
| **SOP citations fabricated** | 1 of 1 (100%) | 0 of 23 | — |
| **Cost @ Haiku 4.5** | $0.066 | $0.069 | +5% |

### The headline finding — AT-3 no-RAG **fabricated** an SOP filename

In the AT-3 no-RAG run (capacity rollover), the agent — pressured by the system-prompt instruction to cite SOPs — invented a plausible-sounding filename:

> *"...per `sop-capacity-rollover-rebooking.md` §Re-booking thresholds..."*

The real file is `sop-capacity-rollover.md`. The "rebooking" suffix is fabricated.

**This is exactly why we built RAG.** Without the retrieval grounding:
- The agent doesn't know the actual filename, so it invents one that *sounds right*.
- The cited "section" doesn't exist either — it's a confident reference to nothing.
- An ops user reading this would not notice unless they tried to open the file.

In the RAG run for AT-3, all 4 cited SOPs (`sop-capacity-rollover.md`, `sop-customer-tier-comms.md`, etc.) are real, with real section names matching the chunked content.

### Where RAG isn't helping (and shouldn't)

- **Token cost.** RAG adds ~1,500 input tokens per turn for SOP context. At Haiku 4.5 prices that's $0.0015 — trivial. At Sonnet 4.6 it's $0.0045 per turn.
- **Latency.** Chroma local search is ~10ms. The token-count bump adds ~1s of LLM time. Net latency cost is negligible.
- **Output length.** Surprisingly *down* with RAG. The agent stops padding generic advice and instead cites + summarizes specific guidance.

## Side-by-side excerpt — AT-1 (customs hold)

Both runs correctly diagnose the missing Commercial Invoice. The difference is in **specificity** and **groundedness**.

**no-RAG output (excerpt):**
> *"You should escalate to the broker if the shipper doesn't respond. Send a customer notification within the SLA window. Track demurrage exposure."*

Generic, plausible — but not grounded in this team's playbook.

**RAG output (excerpt):**
> *"Per `sop-customs-hold-missing-ci.md` §Escalate at thresholds, for a Gold-tier customer like Brookline Apparel, escalate if the shipper is unresponsive >4 hours. Per `sop-customer-tier-comms.md`, Gold tier requires 4-hour acknowledgment SLA. Per `sop-customs-hold-missing-ci.md` §Customer communication template, surface the demurrage start date ($175/day from 2026-04-30) explicitly in the comm — don't bury it for the final invoice."*

Specific. Cited. Auditable. Anchored in the team's actual process.

The full transcripts are in [`docs/phase4-comparison.md`](phase4-comparison.md) and the raw machine-readable record is in [`docs/phase4-comparison-raw.json`](phase4-comparison-raw.json).

## Cost actuals (this phase)

| Item | Cost |
|---|---|
| Initial dev / smoke tests | ~$0.02 |
| Test suite (no LLM calls) | $0.00 |
| Comparison ablation (10 LLM calls) | ~$0.13 |
| **Phase 4 total** | **~$0.15** |
| Cumulative through Phase 4 | **~$0.20 / $20 budget** (1%) |

## What this phase still does NOT do

| Gap | Filled by |
|---|---|
| Tool-layer enforcement of safety (currently soft via system prompt) | Phase 5 |
| Long-term memory across sessions / customer history | Phase 6 |
| Role + tone adaptation | Phase 7 |
| Web UI | Phase 8 |
| Formal evaluation harness with RAGAs (faithfulness, context precision) | Phase 9 |
