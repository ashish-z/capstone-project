# Phase 7 — Adaptive Behavior (Role + Tone)

**Goal:** Move from "the agent talks the same way to everyone" to **"the agent reframes the same data toward the role of the person it's talking to"** — Tech / Finance / Customer — while keeping every safety rail constant.

The rubric for this phase calls out three distinct domains (Finance, Customer, Tech) and "more proactive responses." Phase 7 implements both as a single mechanism: composable persona addenda layered on top of the base system prompt.

## What's new vs. Phase 6

| Capability | Phase 6 | Phase 7 |
|---|---|---|
| Prompt | Single static `SYSTEM_PROMPT` | `BASE_SYSTEM_PROMPT` + persona addendum, composed at agent-build time |
| User roles supported | One implicit (ops associate) | **Three explicit** — `ops_associate`, `finance_partner`, `customer_lead` |
| Per-role response emphasis | None | Each persona reorders sections, adds new ones, and enforces role-specific proactive behavior |
| Mid-session persona switch | n/a | `session.set_persona(name)` + CLI `/role <name>` |
| Persona on session log | n/a | `TurnRecord.persona` |

## The three personas

Mapped to the rubric's required domains:

| Persona | Domain | Lead emphasis |
|---|---|---|
| `ops_associate` | **Tech** (default) | Tactical triage; full SOP citation; action sequencing with expected resolution times |
| `finance_partner` | **Finance** | Demurrage exposure, alternate-carrier rate deltas, waiver opportunities, cost-vs-value framing on every recommendation |
| `customer_lead` | **Customer** | Draft as the centerpiece; tone calibrated to customer tier per `sop-customer-tier-comms.md`; pre-send checklist for Platinum/Gold; tone-calibration explainer |

Each persona declares:
- A **role label** (shown in CLI banner)
- A **prompt addendum** appended to the base prompt
- A **proactive behavior list** the agent is told to do without being asked

```python
# src/freight_copilot/prompts/personas.py
@dataclass(frozen=True)
class Persona:
    name: str
    role_label: str
    description: str
    addendum: str               # appended to base SYSTEM_PROMPT
    proactive_behaviors: list[str]
```

Safety rails (no commits, no fabrication, no over-promising) live entirely in the **base** prompt and are common to every persona — verified by `tests/test_personas.py::test_safety_rails_constant_across_personas`.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  build_system_prompt(persona_name) →                             │
│                                                                  │
│   ┌─────────────────────┐                                        │
│   │ BASE_SYSTEM_PROMPT  │ tools, hard rules, default format,     │
│   │ (constant)          │ citation rules, hedging policy         │
│   └─────────────────────┘                                        │
│              +                                                   │
│   ┌─────────────────────┐                                        │
│   │ persona.addendum    │ "Lead with FINANCIAL EXPOSURE…"        │
│   │ (varies)            │ "TONE CALIBRATION section…"            │
│   └─────────────────────┘                                        │
│              ▼                                                   │
│   ┌─────────────────────┐                                        │
│   │ build_agent(prompt) │ → LangGraph create_react_agent         │
│   └─────────────────────┘                                        │
│                                                                  │
│  AgentSession.set_persona() rebuilds the agent with a new        │
│  prompt but keeps the same checkpointer — message history        │
│  persists across the switch.                                     │
└──────────────────────────────────────────────────────────────────┘
```

## Files added / changed

| File | Status | Purpose |
|---|---|---|
| [`src/freight_copilot/prompts/personas.py`](../src/freight_copilot/prompts/personas.py) | new | Persona registry — three `Persona` dataclasses |
| [`src/freight_copilot/prompts/system.py`](../src/freight_copilot/prompts/system.py) | refactored | `BASE_SYSTEM_PROMPT` constant + `build_system_prompt(persona)` builder |
| [`src/freight_copilot/agent.py`](../src/freight_copilot/agent.py) | updated | `build_agent(persona=)`, `AgentSession(persona=)`, `set_persona()` |
| [`src/freight_copilot/session_logger.py`](../src/freight_copilot/session_logger.py) | updated | `TurnRecord.persona` field |
| [`src/freight_copilot/__main__.py`](../src/freight_copilot/__main__.py) | updated | `/role <name>` CLI command + persona-aware banner |
| [`eval/run_persona_compare.py`](../eval/run_persona_compare.py) | new | Phase 7 demo — same prompt through all three personas |
| [`tests/test_personas.py`](../tests/test_personas.py) | new | 15 tests covering registry, prompt composition, agent integration |

Tests: 58 → **73 passing**.

## Demo — same prompt, three personas

Same input prompt:

> *"Triage shipment FRT-1044. MSC rolled the booking by 7 days. The customer (Hanseatic Coffee, Gold tier) has a delivery promise of 2026-05-30 — what do we need to think about and what do we tell them?"*

Each persona used the same five tool calls (`lookup_shipment`, `recall_shipment_history`, `recall_customer_history`, `search_sops` ×1–2). Same data, different framing.

### Section structure per persona

| `ops_associate` (Tech) | `finance_partner` (Finance) | `customer_lead` (Customer) |
|---|---|---|
| DIAGNOSIS | DIAGNOSIS | DIAGNOSIS |
| KEY FACTS | **FINANCIAL EXPOSURE** ← new | KEY FACTS |
| APPLICABLE SOPs | KEY FACTS | APPLICABLE SOPs |
| RECOMMENDED ACTIONS (ranked) | APPLICABLE SOPs | RECOMMENDED ACTIONS |
| DOWNSTREAM IMPACT | RECOMMENDED ACTIONS (ranked **by cost-benefit**) | DOWNSTREAM IMPACT |
| DRAFT — CUSTOMER COMMUNICATION | DOWNSTREAM IMPACT | DRAFT — CUSTOMER COMMUNICATION |
| | DRAFT — CUSTOMER COMMUNICATION | **TONE CALIBRATION** ← new |
| | | **WHAT TO CONSIDER BEFORE SENDING (Gold Tier Checklist)** ← new |

The differences are:
- `finance_partner` **adds** a top-of-response `FINANCIAL EXPOSURE` section and reframes the action ranking as *"ranked by cost-benefit"*.
- `customer_lead` **adds** `TONE CALIBRATION` and a `WHAT TO CONSIDER BEFORE SENDING (Gold Tier Checklist)` — that "before-send" checklist is the proactive behavior declared in the persona definition.
- All three keep the safety rails: no `commitment_language` findings, no fabricated SOP citations, hedged drafts throughout.

The full transcripts are in [`docs/phase7-persona-compare.md`](phase7-persona-compare.md). Raw machine-readable record: [`docs/phase7-persona-compare.json`](phase7-persona-compare.json).

### Tokens / latency

| Persona | Tools used | In tok | Out tok | Latency |
|---|---|---|---|---|
| `ops_associate` | 5 | 6,850 | 1,807 | 38.6 s |
| `finance_partner` | 5 | 6,802 | 2,048 | 26.7 s |
| `customer_lead` | 4 | 6,140 | 2,048 | 25.9 s |

Persona addenda add ~300 input tokens vs. base. Output length is comparable across personas — the differences are *content*, not *length*.

## Why this design

### Composition over branching
The original tempting approach was three separate system prompts (one per persona). That would have **forked the safety rails** — three places to update if a hard rule changes. Composing a single base + a small addendum keeps the rails in one file and reviewable.

### Mid-session switching preserves message history
`set_persona()` rebuilds the agent (new `create_react_agent` with the new prompt) but reuses the same `MemorySaver` checkpointer. The user can switch from `ops_associate` to `customer_lead` mid-conversation and the agent still remembers what they discussed. Useful when, e.g., the ops associate finishes the diagnosis and hands off to a customer comms colleague.

### Persona on the turn record
Every `TurnRecord` now has a `persona` field. This lets Phase 9 evaluation compare metrics (faithfulness, draft quality, latency) **stratified by persona** — does `customer_lead` produce better-hedged drafts than `ops_associate`? Soon we'll be able to measure.

### "Proactive" = explicit instruction in the addendum
The rubric calls for "more proactive responses." Each persona's addendum has a "Proactive:" line that names the behaviors the agent should do unprompted:
- `ops_associate`: "Search SOPs proactively for the situation."
- `finance_partner`: "If demurrage is accruing, **always** compute exposure and surface waiver-eligibility — don't wait for the user to ask."
- `customer_lead`: "If the customer tier is Platinum or Gold, **always** add a 'what to consider before sending' checklist."

The demo confirms these fire — `customer_lead` produced the Gold Tier Checklist on its own.

## What we learned the hard way

### 1. The agent will keep the *same* response format unless told to reorder

Initially I expected personas to drift the structure naturally. They mostly didn't — Claude is conservative about format unless the prompt explicitly asks for a different one. The fix was to be specific in each addendum: *"Lead with FINANCIAL EXPOSURE as a separate top-of-response section."* Once the addendum dictates ordering, the model complies cleanly.

### 2. Tone and emphasis come for free; structure has to be specified

Adjective-level changes ("more financial framing") came through naturally from the addendum. But getting a *new section* required telling the model the section name. Lesson: persona addenda should specify both the *style* and the *structure* shifts.

### 3. Mid-session switch needs a fresh agent instance

`create_react_agent` bakes the system prompt at build time. There's no API to update it on a live agent. So `set_persona()` builds a new agent with the new prompt and reuses the existing checkpointer. The state stays, the prompt updates. Tested in `test_set_persona_switches_mid_session`.

## Cost actuals (this phase)

| Item | Cost |
|---|---|
| Tests (no LLM, including 15 new persona tests) | $0.00 |
| 3-persona comparison demo (3 LLM calls) | ~$0.04 |
| Smoke / dev iteration | ~$0.02 |
| **Phase 7 total** | **~$0.06** |
| Cumulative through Phase 7 | **~$0.75 / $20** budget (4%) |

## What this phase still does NOT do

| Gap | Filled by |
|---|---|
| Web UI for human-in-the-loop demo | Phase 8 |
| Persona-stratified evaluation metrics (does `customer_lead` produce better drafts than `ops_associate`?) | Phase 9 |
| Auto-detection of persona from user role inference (today: explicit via `/role`) | future work — not in scope |
