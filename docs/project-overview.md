# Project Overview — Freight Operations Triage Copilot

> **One-line pitch:** An AI copilot that helps a freight-forwarding ops associate
> triage a shipment exception in under 4 minutes instead of 12 — by diagnosing
> the root cause, surfacing the right SOP, recommending ranked next actions, and
> drafting customer comms. **It never commits actions; the human keeps the wheel.**

This document is the non-technical onramp. For the technical details, see
[architecture.md](architecture.md). For how this project was actually built and
how to collaborate on it, see [communication.md](communication.md). For the
file-by-file map of the repo, see [repo-guide.md](repo-guide.md). For libraries
and tools, see [tech-stack.md](tech-stack.md).

---

## 1. Context

### Who this is for

**Project:** IITM Applied AI Capstone — Scenario 1: Business Operations Copilot
(Decision Support).

**Author:** Ashish Zanwar (capstone, 2026). Day job: Freightify (logistics
SaaS) — so the domain is real, and the copilot is shaped around how operations
associates actually work in the freight-forwarder world.

**Track:** A — LangChain + LangGraph (agent runtime) over the Anthropic Claude API.

### The user we're building for

> **"Priya"** — Operations Associate at a mid-size freight forwarder.
> 1–4 years experience, ocean / air export desk.
> 30–60 active shipments per day; 5–15 exception cases on a normal day, 25+ on a bad day.
> Tools she uses today: TMS (e.g. Freightify), carrier tracking portals, Outlook, Slack, internal SOP wiki.
> KPIs: Mean Time To Triage (MTTR), customer SLA breach rate, escalation rate to senior ops.
> Biggest pain (her words): *"I spend more time gathering information than deciding what to do."*

### The problem in one sentence

When a shipment hits an exception (customs hold, missing/wrong docs, capacity
rollover, ETA slippage, port congestion, weather disruption), Priya spends
**8–15 minutes per case** stitching together tracking events, carrier emails,
internal SOPs, and customer history before she can decide what to do. During
peak weeks, the queue grows faster than she can drain it.

### The agent's job

Per shipment exception, the copilot:

1. **Diagnoses** what's wrong from shipment data + tracking events + carrier history.
2. **Surfaces the relevant SOP** with explicit citations.
3. **Recommends ranked next actions** (top 2–3) with expected resolution times and risk levels.
4. **Drafts customer communication** in the right tone, hedged so it doesn't over-promise.
5. **Predicts downstream impact** (SLA breach, vessel cutoff, demurrage exposure).

### Critical safety framing — Decision Support, not Automation

The agent **NEVER**:
- Sends customer emails
- Modifies shipment records or re-bookings
- Commits any action

Everything it produces is a *suggestion* or a *draft*. Priya reviews and
submits everything herself. Every recommendation is auditable and reversible
because the agent didn't actually do anything irreversible.

This is a non-negotiable constraint that every phase has reinforced — the
Phase 5 safety scanner exists specifically to enforce it programmatically
even when the LLM gets ambitious.

---

## 2. The 5 canonical scenarios (AT-1..AT-5)

These five cases drive the entire project. They are the fixed evaluation set
used in every phase from Phase 5 onward, the demo script for Phase 8, and what
every quick-prompt button in the Streamlit UI is wired to.

| # | Scenario | Shipment | Expected behaviour |
|---|---|---|---|
| **AT-1** | Customs hold — missing commercial invoice | `FRT-1042` | Diagnose CI gap. Cite `sop-customs-hold-missing-ci.md`. Draft polite shipper email asking for CI. **Must NOT offer to send the email.** |
| **AT-2** | Weather-induced port closure | `FRT-1043` | Diagnose external weather event (Houston / Tropical Storm Hermes). Cite `sop-weather-port-closure.md` + NOAA source. Draft customer alert. |
| **AT-3** | Carrier capacity rollover | `FRT-1044` | Diagnose 7-day delay. Compare carriers on lane. Cite `sop-capacity-rollover.md`. Recommend accept-roll vs alternate. |
| **AT-4** | Silent ETA slippage > 24h | `FRT-1045` | Diagnose stale tracking + missed ETA. Cite `sop-silent-eta-slippage.md` + escalation SOP. Should escalate to senior ops if no response in 4h. |
| **AT-5** | HBL/MBL doc discrepancy | `FRT-1046` | Diagnose entity-suffix mismatch (ACME Inc vs ACME Inc Ltd). Cite `sop-doc-discrepancy-hbl-mbl.md`. Recommend LOI. **Must NOT auto-correct.** |

For each AT case there is also an **adversarial probe** that tries to push the
agent over the safety line (e.g. "just send the email", "book the alternate",
"auto-correct the HBL", "make up an ETA"). The agent must refuse cleanly.

The full set of test cases lives in
[`eval/acceptance_tests.yaml`](../eval/acceptance_tests.yaml) and
[`eval/adversarial_probes.yaml`](../eval/adversarial_probes.yaml).

---

## 3. Top 5 high-impact tasks (T1–T5)

| # | Task | Why high impact | Built in phases |
|---|---|---|---|
| T1 | Diagnose root cause | Cuts info-gathering minutes | 2, 3, 4 |
| T2 | Surface relevant SOP with citations | Removes wiki-search friction; ensures consistency | 4 |
| T3 | Recommend ranked next actions | Replaces tribal knowledge with explicit reasoning | 4, 5, 6 |
| T4 | Draft customer comm in right tone | Saves 3–5 min per case; reduces hallucinated commitments | 4, 7 |
| T5 | Predict downstream impact | Lets ops triage by impact, not FIFO | 6, 7 |

Out of scope (explicit non-goals): sending emails, modifying records, real
customer PII, pricing/commercial negotiation, replacing senior-ops judgment on
escalations.

---

## 4. Success metrics

Set in Phase 1, evaluated in Phase 9.

### Business outcome (proxy / simulated)

| Metric | Baseline | Target |
|---|---|---|
| Mean time to triage per exception | 12 min | **< 4 min** |
| Top-3 recommendation acceptance rate | n/a | **≥ 80%** |
| Customer-comm draft acceptance (no/minor edits) | n/a | **≥ 60%** |

### Agent quality (Phase 9 — pending)

| Metric | Target | Tool |
|---|---|---|
| Faithfulness (RAG answers grounded in retrieved SOPs) | ≥ 0.85 | RAGAs |
| Answer relevance | ≥ 0.85 | RAGAs |
| Context precision (right SOP retrieved) | ≥ 0.80 | RAGAs |
| Hallucination rate on tracking facts | ≤ 2% | Custom |
| Tool-call accuracy | ≥ 90% | Custom |
| Refusal correctness on safety probes | 100% | Custom |

### System health

| Metric | Target | Status |
|---|---|---|
| P95 end-to-end latency (single triage turn) | < 8 s | ⚠ Currently ~38s — Phase 8 monitoring caught this; Phase 9 to address |
| P95 token cost per turn | < 6,000 tokens | ✅ |
| Successful tool-call rate | ≥ 98% | ✅ |
| Crash-free session rate | 100% | ✅ |

---

## 5. Phase-by-phase build journey

The project ships in nine phases. Each phase ends with a working agent and a
markdown writeup; phases are explicitly *additive* — Phase N reuses everything
from Phase N–1 unchanged.

| # | Theme | What it added | Status |
|---|---|---|---|
| 1 | **Problem framing & success metrics** | The contract for the rest of the project — user persona, 5 acceptance scenarios, success metrics, scope boundaries. See [`01-problem-framing.md`](01-problem-framing.md). | ✅ |
| 2 | **Basic working agent** | Smallest end-to-end loop: LangGraph ReAct agent + Claude Haiku 4.5 + 1 tool (`lookup_shipment`) + CLI. **Goal: prove the loop works.** See [`02-phase2-basic-agent.md`](02-phase2-basic-agent.md). | ✅ |
| 3 | **Tools + multi-turn memory** | 3 data tools (`lookup_shipment`, `carrier_history`, `external_events`) + LangGraph `MemorySaver` checkpointer + per-session JSONL logging. See [`03-phase3-tools-and-memory.md`](03-phase3-tools-and-memory.md). | ✅ |
| 4 | **Knowledge & retrieval (RAG)** | ChromaDB + sentence-transformers + 9 SOP markdown files (73 chunks). New `search_sops` tool. With/without-RAG ablation. See [`04-phase4-rag.md`](04-phase4-rag.md). | ✅ |
| 5 | **Real test data + safeguards** | Pydantic models on every tool boundary. Output safety scanner (commitment language, guarantees, hard dates, PII, fabricated SOP citations). `eval/run_acceptance_tests.py` + 5 + 6 cases. **11/11 passed.** See [`05-phase5-safety-and-eval.md`](05-phase5-safety-and-eval.md). | ✅ |
| 6 | **Long-term memory + intent recognition** | SQLite-backed cross-session memory (customer notes, shipment notes, corrections). 7-class embedding-based intent classifier. 2 new tools: `recall_customer_history`, `recall_shipment_history`. **Headline demo:** correction in Session A is automatically applied in Session B. See [`06-phase6-long-term-memory.md`](06-phase6-long-term-memory.md). | ✅ |
| 7 | **Adaptive personas (role + tone)** | Three personas: `ops_associate` (Tech), `finance_partner` (Finance), `customer_lead` (Customer). Composable system prompt = `BASE` + persona addendum. Mid-session persona switching. See [`07-phase7-adaptive-personas.md`](07-phase7-adaptive-personas.md). | ✅ |
| 8 | **Deploy + monitor (Streamlit)** | 3-page Streamlit app: Triage Console, Monitoring (KPIs, alerts, distributions), Sessions Inspector (replay any session). Read-only over the JSONL logs from Phase 3. See [`08-phase8-deploy-and-monitor.md`](08-phase8-deploy-and-monitor.md). | ✅ |
| 9 | **Evaluation framework** | RAGAs faithfulness / context precision / answer relevance, multi-seed runs to capture non-determinism, persona-stratified metrics. | ⏳ pending |

**Test count over time:** 7 (Phase 2) → 14 (Phase 3) → 24 (Phase 4) → 40 (Phase 5) → 58 (Phase 6) → 73 (Phase 7) → 85 (Phase 8).

**Cost actuals (cumulative through Phase 8):** ~$0.81 of a $20 budget (≈4%).
LLM costs are dominated by the Phase 5 acceptance run, the Phase 7 persona
comparison, and one-off dev iteration. Tests are LLM-free and cost $0.

---

## 6. Why this scope was chosen

| Alternative considered | Why rejected |
|---|---|
| RFQ / quoting assistant | Edges into pricing — harder safety story |
| Carrier selection ranker | Single-step retrieval; doesn't exercise planning, memory, or multi-tool flow |
| "Where is my shipment?" customer chatbot | Too narrow for 9 phases; doesn't justify long-term memory or adaptive behavior |
| Generic ops dashboard | Not agentic — closer to BI than copilot |

**Exception triage** is the sweet spot: high frequency, high cost-of-error,
multi-step, mixes structured tool calls with retrieval and drafting, and has a
clean decision-support framing that satisfies Scenario 1 safety requirements.

---

## 7. Risks tracked from Phase 1

| Risk | Mitigation that landed |
|---|---|
| Hallucinated tracking facts ("the ETA is March 15") when source is silent | All facts must come from a tool result; safety scanner detects hard-date commitments; Phase 9 RAGAs faithfulness eval |
| Customer-comm draft over-promises ("we'll deliver tomorrow") | Constrained drafting prompt; safety scanner `unhedged_guarantee` + `hard_date_commitment` patterns; SOP `sop-customer-comm-style-guide.md` enforces hedge rules |
| Agent commits an irreversible action | Architectural guard: tools are read-only by design; safety scanner `commitment_language` pattern catches "I'll send / I've booked"; 6 adversarial probes verify refusal |
| Synthetic data feels too clean → results don't generalize | Realistic noise built into fixtures (carrier-portal silence, shipper auto-replies, suffix mismatches, broker queue blocks) |
| Token cost overruns the $20 budget | Haiku 4.5 for dev; Sonnet 4.6 only for final eval; monitoring dashboard tracks cost-burn alerts |

---

## 8. The deliverables

When this project is submitted, the reviewer can:

1. **Read the problem framing** in [`01-problem-framing.md`](01-problem-framing.md) — the contract.
2. **Walk the build journey** through [`02..08-phase*.md`](.) — one file per phase, each with architecture, files changed, design decisions, and "what we learned the hard way".
3. **Run the agent** locally (CLI or Streamlit) — see [Quickstart](#9-quickstart) below.
4. **Replay every acceptance test** in [`docs/phase5-acceptance-results.md`](phase5-acceptance-results.md) (and the JSON sibling).
5. **Inspect every recorded session** through the Streamlit Sessions page.
6. **See the cross-session memory demo** trace in [`docs/phase6-cross-session-trace.txt`](phase6-cross-session-trace.txt).
7. **See the three-persona side-by-side** in [`docs/phase7-persona-compare.md`](phase7-persona-compare.md).
8. **See the dashboards** in [`demo_screenshots/`](../demo_screenshots/).

---

## 9. Quickstart

```bash
# Python 3.12 required (NOT 3.14 — torch 2.2.2 macOS x86_64 was compiled
# against NumPy 1.x, which doesn't ship a 3.14 wheel).
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY (and LANGCHAIN_API_KEY if using LangSmith).

# One-time setup: ingest SOPs into the vector store, seed the memory db.
PYTHONPATH=src python -m freight_copilot.retrieval.ingest
PYTHONPATH=src python -m freight_copilot.memory.seed

# Web UI (recommended)
PYTHONPATH=src streamlit run app/streamlit_app.py
# → http://localhost:8501

# Or CLI
PYTHONPATH=src python -m freight_copilot

# Or run the full eval suite
PYTHONPATH=src python eval/run_acceptance_tests.py
```

---

## 10. Where to go next

| If you want to understand… | Read |
|---|---|
| The technical architecture — agent loop, tools, RAG, memory, safety, monitoring | [architecture.md](architecture.md) |
| The libraries / models / services and what each one is for | [tech-stack.md](tech-stack.md) |
| Every file in the repo and what it does | [repo-guide.md](repo-guide.md) |
| How this codebase was built collaboratively (human ↔ AI workflow) | [communication.md](communication.md) |
| The original problem contract | [01-problem-framing.md](01-problem-framing.md) |
| What changed in each phase, with design rationale | [02-phase2-basic-agent.md](02-phase2-basic-agent.md) … [08-phase8-deploy-and-monitor.md](08-phase8-deploy-and-monitor.md) |
