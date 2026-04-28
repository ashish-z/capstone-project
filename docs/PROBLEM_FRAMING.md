# Problem Framing — Freight Operations Triage Copilot

**IITM Applied AI Capstone — Scenario 1 (Business Operations Copilot, Decision Support)**
**Author:** Ashish Zanwar · `useitforstudy@gmail.com`

This is the 1-page contract for the project. The full Phase-1 deep-dive
lives in [`01-problem-framing.md`](01-problem-framing.md).

---

## The problem in one paragraph

Operations associates at a mid-size freight forwarder spend **8–15 minutes
per shipment exception** stitching together tracking events, carrier emails,
internal SOPs, and customer history before they can decide what to do.
During peak weeks, the exception queue grows faster than they can drain it.
Most of that 8–15 minutes is *gathering information*, not *deciding*.

## Who we're building for

| Attribute | Value |
|---|---|
| Persona | "Priya" — Ocean / air export ops associate (1–4 yrs experience) |
| Daily volume | 30–60 active shipments; 5–15 exception cases on a normal day |
| Tools today | TMS (e.g. Freightify), carrier portals, Outlook, Slack, internal SOP wiki |
| Typical exceptions | Customs hold, missing/wrong docs, capacity rollover, ETA slippage, port congestion, weather disruption |
| KPIs | Mean Time To Triage (MTTR), customer SLA breach rate, escalation rate |
| Time pressure | Customer SLAs (often 4-hour ack for Gold/Platinum) and vessel cutoffs (hard deadlines) |
| Quoted pain | *"I spend more time gathering information than deciding what to do."* |

## What the agent does — and explicitly doesn't

For each exception, the copilot:
1. **Diagnoses** root cause from shipment record + tracking + carrier notes.
2. **Surfaces the relevant SOP** with explicit filename + section citations.
3. **Recommends 2–3 ranked next actions** with expected resolution times and risk.
4. **Predicts downstream impact** (SLA breach, vessel cutoff, demurrage exposure).
5. **Drafts customer comms** in tone calibrated to the customer's tier, hedged to never over-promise.

**Critical safety framing — Decision Support, not Automation.** The agent
**NEVER** sends emails, books carriers, cancels bookings, or modifies
records. Everything it produces is a *suggestion* or a *draft* that the human
ops associate reviews and submits. The agent's tools are read-only by design;
there is no `update_shipment` tool. That absence is the load-bearing safety
guarantee.

## The 5 canonical acceptance scenarios (AT-1..AT-5)

| # | Scenario | Shipment |
|---|---|---|
| AT-1 | Customs hold — missing Commercial Invoice | `FRT-1042` |
| AT-2 | Weather-induced port closure | `FRT-1043` |
| AT-3 | Carrier capacity rollover | `FRT-1044` |
| AT-4 | Silent ETA slippage > 24 h | `FRT-1045` |
| AT-5 | HBL/MBL document discrepancy | `FRT-1046` |

Each AT case has a paired **adversarial probe** (e.g. *"Just send the
customer email for me"*, *"Auto-correct the HBL"*) that tries to push the
agent past the safety line. The agent must refuse cleanly.

## Success metrics — what "good" looks like

### Business outcome (proxy / simulated)

| Metric | Baseline | Target |
|---|---|---|
| Mean time to triage per exception | 12 min | **< 4 min** |
| Top-3 recommendation acceptance | n/a | ≥ 80% |
| Customer-comm draft accepted with no/minor edits | n/a | ≥ 60% |

### Agent quality (Phase 9 measured)

| Metric | Target | Measured |
|---|---|---|
| Tool-call accuracy | ≥ 90% | **100%** ✅ |
| RAGAs context precision | ≥ 0.80 | **0.933** ✅ |
| Hallucination rate (steady-state) | ≤ 2% | **0%** ✅ |
| Refusal correctness on adversarial probes | 100% | **83.3%** — one repeatable failure on ADV-5 |
| P95 latency | < 8 s | 38.6 s ❌ |

### System health

| Metric | Target | Measured |
|---|---|---|
| Successful tool-call rate | ≥ 98% | 100% ✅ |
| Crash-free session rate | 100% | 100% ✅ |

The full reasoning behind passes/fails — including why RAGAs faithfulness is
a structural mismatch, where the 38.6 s latency goes, and the ADV-5 root
cause — is in the [Evaluation Report](EVALUATION_REPORT.md).

## Out of scope

| Non-goal | Why excluded |
|---|---|
| Sending customer emails | Violates decision-support framing |
| Modifying shipment records | Same |
| Real customer PII | Synthetic/fixture data only |
| Pricing / commercial decisions | Different risk profile |
| Replacing senior-ops escalations | Wrong tool for the job |

## Why this scope was chosen

Exception triage is the sweet spot: high frequency (5–15× per day per
associate), high cost-of-error, multi-step, mixes structured tool calls
with retrieval and drafting, and has a clean decision-support framing that
satisfies Scenario-1 safety requirements. Alternatives we rejected — RFQ /
quoting (edges into pricing), single-step carrier ranking (doesn't exercise
multi-tool planning), generic ops dashboard (not agentic) — would have
required either a weaker safety story or a thinner technical surface.
