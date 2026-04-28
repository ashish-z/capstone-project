# End-to-End Walkthrough — Product View, Tech View, Request Flows

This document is for someone who wants to understand the entire project in two
ways: first as a **product leader** (what's the problem, who hurts, how does
this fix it?), then as a **tech leader** (which library does what, why was it
chosen, how do they fit together?). It also includes step-by-step request
flows for all three personas so you can see the operations sequence end to end.

If you want the file map of the repo, see [`repo-guide.md`](repo-guide.md).
If you want the implementation-detail architecture, see
[`architecture.md`](architecture.md).

---

# PART 1 — PRODUCT LEADER VIEW

## 1. The problem (in plain language)

A **freight forwarder** is the company that arranges to physically move a
shipment from the seller (in one country) to the buyer (in another). They
don't own the ships, planes, or trucks — they just orchestrate them.

Every shipment goes through dozens of handoffs:

```
Shipper warehouse → trucker → port of origin → customs export →
ocean carrier → ocean transit → port of destination → customs import →
broker → trucker → consignee warehouse
```

Most shipments move smoothly. **Some don't** — and when they don't, those are
called **exceptions**. Examples:

| Exception | What's happening |
|---|---|
| Customs hold | Authority won't release the goods until a missing document arrives |
| Capacity rollover | Carrier put your container on the *next* sailing instead of the booked one — you lose 7 days |
| Silent ETA slippage | The shipment was supposed to arrive yesterday and the carrier portal hasn't updated in 36 hours |
| Document discrepancy | The Bill of Lading and the customs paperwork have slightly different consignee names — release blocked |
| Weather / port closure | Storm closed the port; nothing moves until reopen |

When an exception fires, an **Operations Associate** has to triage it. Meet
**Priya**:

> Priya, ops associate at a mid-size freight forwarder. 1–4 years experience.
> Manages 30–60 active shipments per day. On a normal day, 5–15 of them have
> exceptions. On a bad day, 25+.
>
> For each exception, she has to:
> 1. Open the TMS, read the shipment record, the tracking events, the carrier emails.
> 2. Open the SOP wiki, find the relevant playbook.
> 3. Check the customer's history (have we seen this before? what tier are they? what's their SLA?).
> 4. Decide what to do.
> 5. Draft a customer email if needed.
> 6. Hand off or self-execute the action.
>
> **This takes her 8–15 minutes per case.** Most of that time is *gathering
> information*, not *deciding*. During peak weeks, the queue grows faster
> than she can drain it. Her own words: *"I spend more time gathering
> information than deciding what to do."*

There's also pressure from above:

| Pressure | Reality |
|---|---|
| Customer SLA | Often 4-hour acknowledgment for high-tier customers (Gold, Platinum) |
| Vessel cutoff | Hard deadline — miss it and you wait another sailing |
| Demurrage | Container sitting idle at port costs money per day, paid by *somebody* |
| KPIs | She's measured on Mean Time To Triage, SLA breach rate, escalation rate |

So the problem is **not that ops associates can't make decisions**. They're
good at decisions. The problem is they're spending most of their day
gathering context to *make* the decision.

---

## 2. The solution (in plain language)

We built a **decision-support copilot**. It does NOT take the action — Priya
keeps doing that. It does the **gathering** for her, and presents the result
in a structured, citable, ranked form.

For each exception, the copilot:

| Step | What it does | What it returns |
|---|---|---|
| 1 | Diagnose the root cause | "Customs hold; missing Commercial Invoice" |
| 2 | Pull all the facts that matter | Tracking events, carrier notes, customer tier, SLA, demurrage exposure |
| 3 | Find the relevant SOP | "Per `sop-customs-hold-missing-ci.md` §Escalation, Gold tier escalates after 4 hours of shipper silence" |
| 4 | Recommend the next 2–3 actions, ranked | (a) Email shipper for CI, (b) Notify consignee, (c) Check broker queue |
| 5 | Predict downstream impact | "SLA breach risk: 27 hours from now. Demurrage starts in 3 days at $175/day." |
| 6 | Draft the customer email | Hedged language, tier-appropriate tone, never over-promising |

**Critical constraint — and this is the whole product positioning:**

> The copilot **NEVER commits actions**. It NEVER sends an email. It NEVER
> books a carrier. It NEVER cancels a booking. Everything it produces is a
> *suggestion* or a *draft*. Priya reads it, edits if needed, and submits
> herself.

This isn't a limitation we're sad about — it's the core product positioning.
Why?

| Reason | Explanation |
|---|---|
| **Trust** | Ops associates don't trust black-box automation that can email customers on its behalf. They *do* trust a tool that helps them think faster. |
| **Auditability** | If the agent never acts, every output is a draft a human reviewed. Nothing irreversible can happen. |
| **Regulatory** | Freight is a compliance-heavy domain (customs, export controls). "AI sent the customs declaration" is not a sentence anyone wants to defend. |
| **Mistakes are recoverable** | An incorrect *draft* is harmless — Priya catches it. An incorrect *sent email* is a customer escalation. |

This framing — "decision support, not automation" — is what makes the
product safe to ship.

---

## 3. Three personas, one agent

The copilot serves three different roles within the freight forwarder. Same
underlying data and tools — different framing of the answer.

| Persona | Real-world role | What they need most |
|---|---|---|
| **Ops Associate** (Tech) | Triages exceptions all day | Tactical: diagnosis, ranked actions, next steps |
| **Finance / Cost-Recovery Partner** | Owns the P&L impact of exceptions | Demurrage exposure, rate deltas if we re-route, waiver opportunities |
| **Customer Communications Lead** | Owns the customer-facing message | A polished draft email, tone-calibrated to the customer's tier, with hedging language |

Each role asks **different questions about the same shipment**, and gets a
**differently-framed answer**, but the underlying facts and the safety rails
are identical.

---

## 4. What "good" looks like — measurable

| Outcome | Today (manual) | With copilot (target) |
|---|---|---|
| Mean time to triage per exception | 12 min | < 4 min |
| Top-3 recommendation acceptance rate (do ops actually do what it suggested?) | n/a | ≥ 80% |
| Customer-comm draft accepted with no/minor edits | n/a | ≥ 60% |
| Hallucinated tracking facts (agent invents dates/IDs) | n/a | ≤ 2% |
| Refusal correctness on commit-style asks ("just send it") | n/a | 100% |

These are not aspirations — they're written into the success-metrics table in
[`01-problem-framing.md`](01-problem-framing.md) and they're what the Phase 9
evaluation will grade against.

---

## 5. Why this scope, and not something else

Other things we considered and why we *didn't* build them:

| Alternative | Why we rejected it |
|---|---|
| Quoting / pricing assistant | Edges into commercial decisions. Hard safety story. |
| Carrier ranking calculator | Single-step. Doesn't exercise multi-tool planning, memory, or drafting. |
| Customer-facing "Where's my shipment?" chatbot | Too narrow. Wouldn't justify long-term memory or persona adaptation. |
| Ops dashboard with charts | Not agentic — closer to BI. |

**Exception triage is the sweet spot:** high frequency (5–15× per day per
associate), high cost-of-error, multi-step, mixes structured tool calls with
retrieval and drafting, and has a clean decision-support framing.

---

# PART 2 — WHERE USERS TOUCH THE SYSTEM

The system is delivered through **three surfaces**. Same underlying agent in
all three.

```
┌─────────────────────────────────────────────────────────────┐
│  WHERE THE USER TYPES OR CLICKS                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  A. Streamlit web app  http://localhost:8501  (3 pages)     │
│     ├─ 🚚 Triage Console   ← this is where work happens     │
│     ├─ 📊 Monitoring       ← read-only ops dashboard        │
│     └─ 🔍 Sessions         ← read-only audit / replay       │
│                                                             │
│  B. CLI terminal:  python -m freight_copilot                │
│     Same agent, no UI. Slash commands /reset, /role.        │
│                                                             │
│  C. Eval scripts:  python eval/<script>.py                  │
│     Developer-facing. Runs the agent against fixed prompts. │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

The **primary** user-facing surface is the Streamlit Triage Console. The
other two pages are operational/audit views, not where work happens.

---

# PART 3 — ENTITY-TO-ENTITY COMMUNICATION

Before we walk the per-persona flows, here's the full picture of who talks to
whom. Read this once and the per-persona flows will be obvious.

```
                     ┌──────────────────────────────────────────────────┐
                     │  END USER                                        │
                     │  (Priya — ops associate, finance, or customer)   │
                     └─────────────────┬────────────────────────────────┘
                                       │
                                       │  types text / clicks button
                                       ▼
                     ┌──────────────────────────────────────────────────┐
                     │  STREAMLIT WEB APP  (or CLI — same role)         │
                     │  - chat input                                    │
                     │  - persona selector                              │
                     │  - quick-prompt buttons                          │
                     │  - renders streamed events                       │
                     └─────────────────┬────────────────────────────────┘
                                       │
                                       │  session.stream_turn(user_input)
                                       ▼
        ┌────────────────────────────────────────────────────────────────┐
        │  AGENTSESSION  (one per chat session, identified by thread_id) │
        │  - classifies user intent                                      │
        │  - persists corrections                                        │
        │  - runs the LangGraph ReAct loop                               │
        │  - scans the response for safety issues                        │
        │  - emits structured events back to UI                          │
        │  - logs the turn to JSONL                                      │
        └─────────────┬─────────────────┬──────────────────┬─────────────┘
                      │                 │                  │
   ┌──────────────────┘                 │                  └──────────────────┐
   ▼                                    ▼                                     ▼
┌──────────────────────┐  ┌────────────────────────────────────┐  ┌──────────────────────┐
│  ANTHROPIC CLAUDE    │  │  6 TOOLS — read-only, by design    │  │  SAFETY SCANNER      │
│  (Haiku 4.5)         │  │                                    │  │  pattern regex +     │
│  cloud LLM           │  │  DATA TOOLS                        │  │  SOP citation        │
│                      │  │  ├─ lookup_shipment                │  │  cross-check         │
│  decides which tool  │  │  ├─ carrier_history                │  │  (runs on every      │
│  to call next; emits │  │  └─ external_events                │  │   final response)    │
│  the final response  │  │                                    │  └──────────────────────┘
│                      │  │  RAG TOOL                          │
└──────────────────────┘  │  └─ search_sops                    │
                          │                                    │
                          │  MEMORY TOOLS                      │
                          │  ├─ recall_shipment_history        │
                          │  └─ recall_customer_history        │
                          └──┬─────┬─────┬──────────────────┬──┘
                             │     │     │                  │
              ┌──────────────┘     │     │                  └──────────────┐
              ▼                    ▼     ▼                                 ▼
  ┌────────────────────┐  ┌─────────────────────┐              ┌────────────────────┐
  │  data/             │  │  ChromaDB           │              │  data/             │
  │  shipments/*.json  │  │  chroma_db/         │              │  memory.sqlite3    │
  │  lane_history.json │  │  73 SOP chunks      │              │  3 tables:         │
  │  external_events…  │  │  (built by ingest)  │              │  customer_notes,   │
  │  (5 fixtures + 2)  │  │                     │              │  shipment_notes,   │
  └────────────────────┘  └─────────────────────┘              │  corrections       │
                                                               └────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────────┐
  │  logs/session-<thread_id>.jsonl                                            │
  │  (AgentSession appends one JSON line per turn — single source of truth     │
  │   the Monitoring + Sessions pages read from)                               │
  └────────────────────────────────────────────────────────────────────────────┘
```

A few things to notice:

1. **The user only ever talks to the Streamlit app** (or CLI). They never see
   the LLM, the tools, or the data stores directly.
2. **The LLM never reads files directly.** It only reads what tools return.
   This is what makes the safety story credible — every fact in the response
   came from a Pydantic-validated tool result, traceable in the JSONL log.
3. **Tools are read-only by design.** There is no `update_shipment` tool.
   That absence is the load-bearing safety guarantee.
4. **JSONL logs are the single source of truth** that the dashboards read
   from. No parallel logging system.

---

# PART 4 — END-TO-END REQUEST FLOWS, PER PERSONA

Each flow uses the same shipment (FRT-1042 — customs hold, missing
Commercial Invoice). Same data, three different framings.

For all three, the **mechanism** is identical:
- Intent classified → correction maybe persisted → LangGraph ReAct loop
  alternates LLM ↔ tools → safety scan → response shown → log written.

The **persona system prompt addendum** is what changes the response shape.

---

## Flow A — Persona: `ops_associate` (Tech)

**Goal:** Priya needs a fast tactical triage so she can act in the next 2 minutes.

### Sequence diagram

```
USER (Priya, ops_associate)
  │
  │  [1]  Click sidebar quick-prompt "AT-1 — Customs hold"
  │       (or types the same prompt manually)
  ▼
STREAMLIT  (app/streamlit_app.py)
  │
  │  [2]  Sets pending_prompt in session_state and reruns
  │  [3]  Captures prompt = "Triage shipment FRT-1042. Customs hold —
  │        what's wrong, what should I do next, draft a customer email"
  │
  │  [4]  session.stream_turn(prompt)
  ▼
AGENTSESSION  (src/freight_copilot/agent.py)
  │
  │  [5]  classify_intent(prompt)
  │       └─ embed prompt with all-MiniLM-L6-v2
  │       └─ cosine-match against 7 centroids
  │       └─ result: intent="triage_request", confidence=0.71
  │       └─ EMIT { type: "intent", ... }                      → UI shows 🧭 intent badge
  │
  │  [6]  Not a correction, skip persistence step.
  │
  │  [7]  Build TurnRecord. Mark turn_started_ms.
  │
  │  [8]  agent.stream({messages: [user msg]}, thread_id=...)
  ▼
LANGGRAPH REACT LOOP   (langgraph.prebuilt.create_react_agent)
  │
  │  [9]  LLM (Claude Haiku 4.5) reads:
  │       - BASE_SYSTEM_PROMPT + ops_associate addendum
  │       - the user message
  │       Decides: "I need shipment data. Call lookup_shipment."
  │       └─ EMIT { type: "tool_call", name: "lookup_shipment", args: {...} }
  ▼
TOOL — lookup_shipment("FRT-1042")
  │
  │  [10] Read data/shipments/FRT-1042.json
  │  [11] Validate against ShipmentRecord (pydantic)
  │  [12] Return JSON to the LLM
  │       └─ EMIT { type: "tool_result", ... }
  ▼
LLM
  │  [13] "Customer is Brookline Apparel Co (Gold tier, 4h SLA).
  │        I should check what we know about them historically."
  ▼
TOOL — recall_customer_history("Brookline Apparel Co")
  │  [14] Query SQLite memory.sqlite3
  │  [15] Return notes + corrections JSON
  ▼
LLM
  │  [16] "I see notes about Aurora Textiles being slow on CI.
  │        Now find the SOP for customs holds."
  ▼
TOOL — search_sops("customs hold missing commercial invoice", k=4)
  │  [17] Embed query with all-MiniLM-L6-v2
  │  [18] Query ChromaDB (cosine distance over 73 chunks)
  │  [19] Return top-4 chunks with {source, section, text, distance}
  ▼
LLM
  │  [20] "I have what I need. Compose response."
  │       Produces structured markdown:
  │         DIAGNOSIS — Customs hold, missing CI, broker queue blocked
  │         KEY FACTS — vessel, dates, customer tier, demurrage
  │         APPLICABLE SOPs — sop-customs-hold-missing-ci.md
  │         RECOMMENDED ACTIONS — ranked, with risk + ETA
  │         DOWNSTREAM IMPACT — SLA breach 27h, demurrage in 3d
  │         DRAFT — CUSTOMER COMMUNICATION (terse — ops_associate persona)
  ▼
AGENTSESSION
  │  [21] safety.scan_response(text)
  │       └─ regex pattern scan (commitment, guarantee, hard date, PII)
  │       └─ SOP filename cross-check vs data/sops/*.md
  │       └─ no findings → no event emitted
  │
  │  [22] EMIT { type: "final", text: <markdown> }
  │
  │  [23] _persist_turn_summary
  │       └─ first paragraph of response → shipment_notes row in SQLite
  │
  │  [24] SessionLogger.write(TurnRecord)
  │       └─ append one JSON line to logs/session-<thread_id>.jsonl
  ▼
STREAMLIT
  │  [25] As each event arrives, update the live status panel:
  │       "🧭 intent → 🔧 lookup_shipment → 🔧 recall_customer_history →
  │        🔧 search_sops → ✓ done"
  │  [26] Render the final markdown in the chat bubble.
  │  [27] Persist events to st.session_state["events"] so the turn
  │       survives the next st.rerun()
  ▼
USER
  │  [28] Reads:
  │       - Diagnosis (one paragraph)
  │       - Key facts (cited)
  │       - Applicable SOP (filename + section)
  │       - 3 ranked actions with ETAs and risk
  │       - Downstream impact (SLA + demurrage exposure)
  │       - A short draft email
  │  [29] Decides what to do. Sends the email *herself* if she likes the draft.
```

**What Priya gets:** ranked actions she can execute in the next 5 minutes,
with the SOP citations to defend the call if asked.

---

## Flow B — Persona: `finance_partner` (Finance)

**Goal:** Same shipment, but the user is a finance analyst worried about
dollar exposure.

### What changes vs Flow A

The mechanism is **identical** to steps 1–28 above. The only difference is
step [9] — the LLM reads a different system prompt (BASE +
`finance_partner.addendum` instead of BASE + `ops_associate.addendum`).

The finance persona's addendum tells the LLM:

> *"Lead with FINANCIAL EXPOSURE as a separate top-of-response section:
> demurrage start date, daily rate, exposure to date, projected exposure if
> delay extends 5 days; alternate-carrier rate delta; estimated
> service-recovery cost if SLA is missed. Make every recommendation include
> a cost/value framing. If demurrage is accruing, ALWAYS compute exposure
> and surface waiver-eligibility — don't wait for the user to ask."*

### Sequence diagram (only the response-shaping step differs)

```
[1]–[19]   Same as Flow A.

LLM
  │  [20'] Compose response — finance addendum reorders the structure:
  │         FINANCIAL EXPOSURE   ← NEW, leads
  │           - demurrage starts 2026-04-30 at $175/day
  │           - if hold extends 5 days: $875 exposure
  │           - alternate carrier rate delta: +$300/container
  │           - per sop-demurrage-management.md: waiver eligible if hold > 48h
  │         DIAGNOSIS
  │         KEY FACTS
  │         APPLICABLE SOPs
  │         RECOMMENDED ACTIONS (ranked by cost-benefit)
  │         DOWNSTREAM IMPACT
  │         DRAFT — CUSTOMER COMMUNICATION (de-emphasized)
  ▼
[21]–[29]  Same as Flow A.
```

**What the finance partner gets:** dollars exposed, dollars recoverable, and
an explicit waiver opportunity.

---

## Flow C — Persona: `customer_lead` (Customer)

**Goal:** Same shipment, but the user owns the customer relationship and
needs to send a polished email *today*.

### What changes vs Flow A

Same mechanism, different system-prompt addendum. The customer addendum
tells the LLM:

> *"Lead with the DRAFT — CUSTOMER COMMUNICATION section. Make it the
> centerpiece, not an afterthought. Tailor tone to the customer tier per
> sop-customer-tier-comms.md (Platinum/Gold = formal-empathetic, 4–8
> paragraphs; Silver/Bronze shorter). Apply every rule from
> sop-customer-comm-style-guide.md: lead with impact, not cause; hedge
> timelines; cite external sources for weather/labor; disclose financial
> exposure proactively; end with a concrete next step + cadence. Provide a
> TONE CALIBRATION section explaining why the draft was framed this way. If
> tier is Platinum or Gold, ALWAYS add a 'what to consider before sending'
> checklist."*

### Sequence diagram (only the response-shaping step differs)

```
[1]–[19]   Same as Flow A. Tools called are the same set.

LLM
  │  [20''] Compose response — customer addendum reorders the structure:
  │          DRAFT — CUSTOMER COMMUNICATION   ← NEW lead
  │            Subject: …
  │            <hedged, tier-appropriate body, ~6 paragraphs>
  │
  │          TONE CALIBRATION   ← NEW
  │            "Brookline Apparel is Gold tier. Per
  │             sop-customer-tier-comms.md, Gold gets formal-empathetic,
  │             4–8 paragraphs, with explicit timeline hedging."
  │
  │          WHAT TO CONSIDER BEFORE SENDING (Gold Tier Checklist)   ← NEW
  │            - Did you confirm CI ETA with the shipper?
  │            - Has procurement@brookline-apparel.com been included? …
  │
  │          DIAGNOSIS (terse)
  │          KEY FACTS
  │          RECOMMENDED ACTIONS (terse)
  ▼
[21]–[29]  Same as Flow A.
```

**What the customer-comms lead gets:** a sendable draft, a one-paragraph
explanation of *why* the draft is shaped this way, and a checklist that
stops them from sending something that violates a tier SLA.

---

## Why three personas, same agent, same data?

The single most important insight from Phase 7:

> **The data and the safety rails are constant. Only the framing changes.**

| What's identical across personas | What changes per persona |
|---|---|
| The 6 tools | Which sections lead the response |
| The data they return | Which sections get extra detail |
| The safety scanner + patterns | What "proactive behavior" the agent does unprompted |
| The LLM (Haiku 4.5, temp 0) | The number of paragraphs in the draft |
| The eval suite (AT-1..AT-5) | — |

This means the safety guarantees for `ops_associate` automatically extend to
the other two personas — they share the same base prompt and the same scanner.

---

## Cross-session memory flow (bonus — Phase 6 demo)

This isn't a single-turn flow — it spans two separate Streamlit sessions
(or two CLI sessions). It's how the agent "learns" from a past correction.

```
SESSION A (Monday morning)
  USER: "Triage FRT-1042"
  AGENT: <does normal triage assuming Brookline = Gold>

  USER: "Actually, Brookline got promoted to Platinum last week, not Gold."
  AGENT.classify_intent → "correction" (conf=0.43)
  AGENT.extract_entity → matches known customer "Brookline Apparel Co"
  AGENT.persist_correction → INSERT INTO corrections (
                              entity_kind="customer",
                              entity_id="Brookline Apparel Co",
                              correction="The customer is Platinum tier, not Gold..."
                            )
  AGENT: "Correction recorded. Will apply to future triages of Brookline."
  SESSION A ENDS  (browser closed, process exits)

──────────────  one hour later  ──────────────

SESSION B (different thread_id, fresh process — no in-memory link to A)
  USER: "Looking at FRT-1042 again. Anything I should know?"
  AGENT calls lookup_shipment(FRT-1042)         → tier="Gold" in fixture
  AGENT calls recall_customer_history(...)      → reads SQLite
                                                → finds Session A's correction
  AGENT: "IMPORTANT CORRECTION: Brookline is Platinum, not Gold (per
          correction recorded in Session A). The shipment record still
          shows Gold but you should treat them as Platinum for SLA
          and escalation purposes."
```

The persistence boundary is the SQLite db. The data flows:

```
Session A: user input → intent="correction" → SQLite INSERT
Session B: agent ReAct loop → recall_customer_history tool → SQLite SELECT
           → LLM sees the correction → applies it in response
```

This is what makes the agent feel like it has institutional memory across
days of use, not just a single conversation.

---

# PART 5 — TECH LEADER VIEW (every component, from scratch)

For each technology in the stack, I'll answer four questions:
1. **What is it** (assume reader has never heard of it)?
2. **Why do we need that kind of thing**?
3. **Why specifically this one** (over alternatives)?
4. **Where do we use it in the project**?

---

## 5.1 Anthropic Claude API — the LLM

**What is it?**
A **Large Language Model** is a neural network that takes a chunk of text as
input and predicts what text should come next. Trained on enormous corpora
of text from the internet, books, code, and more.

**Anthropic** is an AI company; **Claude** is their family of LLMs. Within
Claude:
- **Haiku 4.5** — small, fast, cheap. Good for tool-use loops.
- **Sonnet 4.6** — larger, more capable, more expensive. Good for high-fidelity drafts and final demos.
- **Opus** — the largest, most expensive. We don't use it here.

**Why do we need an LLM?**
The whole product premise is "diagnose what's wrong, recommend actions, draft
an email" — these are open-ended language tasks. There's no rule-based
program that can do them. Only an LLM, instructed and grounded with the right
context, can produce flexible structured natural-language output.

**Why specifically Claude (not OpenAI's GPT)?**
- The IITM cohort scenario is built around Anthropic; mixing providers
  weakens the prompt-caching/cost story.
- Claude has strong tool-use behavior — it follows the structured
  `tool_calls` format reliably, which matters because our agent is a
  loop of tool calls.
- Anthropic's safety guidance ("don't commit actions" framing) is well-aligned
  with our decision-support positioning.
- Free starting credits for the cohort.

**Where in the project?**
- `src/freight_copilot/agent.py` instantiates `ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0, max_tokens=2048)`.
- Every "thinking" step the agent takes — deciding which tool to call,
  composing the final response — is a Claude API call.
- Cost so far across all 8 phases: ~$0.81 of a $20 budget. Each triage turn
  is ~$0.01–$0.03.

---

## 5.2 LangChain — the LLM-app library

**What is it?**
A Python library that wraps LLM providers (Anthropic, OpenAI, …) with
common primitives:
- `Tool` — a function the LLM can call.
- `ChatModel` — wrapper around an LLM provider's chat API.
- `Embedding` — wrapper around embedding-model APIs.
- `TextSplitter` — utilities for chunking long documents.
- `Document` — a piece of text + metadata.

**Why do we need it?**
Without LangChain, you'd have to:
- Hand-write the JSON schema each tool exposes to the LLM.
- Manually format the chat messages with the right role/content shapes for
  Anthropic's API.
- Manually parse the LLM's tool-call responses into Python function calls.
- Hand-write the markdown chunker.

LangChain makes all of that one decorator (`@tool`) and one constructor
(`ChatAnthropic(...)`).

**Why specifically LangChain (not LlamaIndex)?**
- The IITM rubric's Track A explicitly calls for LangChain + LangGraph.
- LangChain has the larger ecosystem and the better Anthropic integration today.
- LlamaIndex is more retrieval-focused; we need agent + retrieval, and
  LangChain gives us both with one tooling surface.

**Where in the project?**
- `from langchain_core.tools import tool` — the decorator that turns each
  Python function in `tools/` into an LLM-visible tool. The function's
  docstring becomes the tool spec the LLM reads.
- `from langchain_anthropic import ChatAnthropic` — the chat model wrapper.
- `from langchain_text_splitters import RecursiveCharacterTextSplitter` —
  the markdown chunker used in `retrieval/ingest.py`.

---

## 5.3 LangGraph — the agent runtime

**What is it?**
A library (built on LangChain) that lets you describe an LLM agent as a
**state machine / graph**. Each node is a step (e.g. "call the LLM", "execute
a tool"); each edge is a transition. LangGraph runs the graph: at each step
it asks the LLM what to do next, and routes accordingly.

**Why do we need a "graph" for an agent?**
Because a real agent isn't one LLM call. It's a **loop**:

```
1. LLM reads user input + tools available.
2. LLM decides: "I need data — call tool X."
3. Tool X runs, returns JSON.
4. LLM reads the JSON, decides: "I also need the SOP — call tool Y."
5. Tool Y runs, returns JSON.
6. LLM reads, decides: "I have enough — produce the final answer."
```

This loop is called **ReAct** (Reason + Act). LangGraph implements it via
`create_react_agent(...)` with all the boilerplate (loop control, message
history, parallel tool calls, streaming) handled for you.

**Why also a checkpointer?**
A multi-turn conversation needs the LLM to remember what was said in
previous turns. LangGraph's `MemorySaver` stores the message history per
`thread_id` so calling `agent.stream(input, thread_id=tid)` resumes from the
prior state.

**Why specifically LangGraph (not a hand-rolled loop)?**
- The IITM rubric Track A specifies it.
- It's well-tested, supports streaming events (which we use for the live
  Streamlit trace), supports parallel tool calls if we ever want them.
- We get checkpointing for free.

**Where in the project?**
- `from langgraph.prebuilt import create_react_agent` — used in
  `agent.py:build_agent()`.
- `from langgraph.checkpoint.memory import MemorySaver` — instantiated per
  `AgentSession`.
- LangGraph emits structured events as the LLM thinks and tools run; we
  re-emit them upward through `stream_turn()` so the UI can render a live
  trace.

---

## 5.4 ChromaDB — the vector database (the SOP index)

**What is a vector database?**
A normal database stores rows of structured data — strings, numbers, dates.
A **vector database** stores rows where one column is a list of numbers (a
"vector"). You query it not with `WHERE source = 'X'` but with "give me the
rows whose vectors are *closest* to this query vector".

**What do you mean by "closest"?**
You convert text → numeric vector using an **embedding model** (see §5.5).
The clever part: a good embedding model produces *similar* vectors for
*similar meanings*. So:
- "customs hold" and "customs detention" have nearby vectors (synonymous).
- "customs hold" and "vessel cutoff" have far-apart vectors (different concepts).

When we search, we embed the query the same way and ask the database for
the nearest vectors. Distance is **cosine** (smaller = more similar).

**Why do we need this?**
Our SOP corpus is 9 markdown files. When the user asks *"what's our policy
on customs holds?"*, we need to find the right SOP. Naive substring search
fails when the user's wording doesn't match the document's wording. Vector
search finds **semantically similar** text regardless of wording.

This pattern — embed-and-store-at-ingest, embed-and-search-at-query — is
called **RAG** (Retrieval-Augmented Generation).

**Why specifically ChromaDB?**
- **Local-first.** It runs as a Python library writing to a folder on disk
  (`chroma_db/`). No cloud service, no API keys.
- **Free.** Open source.
- **Persistent.** State survives restart.
- **Cosine distance built in.** No need to implement.
- **Supported by LangChain.** Drop-in.
- **Right size for our 73 chunks.** A managed cloud DB would be overkill.

**Why not Pinecone / Weaviate / Qdrant?**
Those are managed cloud DBs. Worth it at hundreds of thousands of vectors.
At 73, ChromaDB local is faster and free.

**Where in the project?**
- `chroma_db/` (gitignored) — the on-disk index.
- `src/freight_copilot/retrieval/store.py` — wraps ChromaDB with our
  collection (`freight_sops`) and the embedding function.
- `src/freight_copilot/retrieval/ingest.py` — the script that chunks the 9
  SOPs into 73 chunks and writes them to Chroma. Run once via
  `python -m freight_copilot.retrieval.ingest`.
- `src/freight_copilot/tools/search_sops.py` — the LLM-visible tool that
  queries Chroma and returns top-k chunks.

---

## 5.5 sentence-transformers / all-MiniLM-L6-v2 — the embedding model

**What is an embedding model?**
A neural network that takes text and outputs a fixed-size vector of numbers.
Same input → same vector. Similar inputs → similar vectors. The whole point
is to convert "meaning" into geometry so vector databases can do similarity
search.

**What is sentence-transformers?**
A Python library on top of Hugging Face's `transformers` that specializes in
producing **sentence-level** embeddings (rather than word-level). It comes
with hundreds of pre-trained models.

**What is all-MiniLM-L6-v2?**
A specific small embedding model. Specs:
- 384-dimensional output vector
- ~80 MB on disk
- Runs on CPU in ~30ms per sentence
- General-purpose semantic similarity

**Why this one?**
- **Tiny + fast** — no GPU needed.
- **Good enough quality** for our 9-SOP corpus.
- **Free** — no API costs (vs OpenAI/Anthropic embedding APIs).
- **Reusable** — same model is used both for RAG embedding AND the intent
  classifier (§5.6). One model loaded, two purposes.

**Where in the project?**
- Loaded by ChromaDB's `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`.
- Loaded again (lazily) by `memory/intent.py` for classifying user intent.
- The model file is downloaded on first use to `~/.cache/huggingface/`.

---

## 5.6 The intent classifier — embeddings reused

**What is it?**
A 7-class classifier that decides what kind of message the user just sent
(`triage_request`, `follow_up`, `policy_question`, `draft_request`,
`correction`, `commit_request`, `meta`).

**How does it work?**
- For each intent class, we hand-curate 6 example prototype phrases.
- We embed all 6 with all-MiniLM-L6-v2, mean-pool them → one **centroid** vector per class.
- For each user input, embed it, compute cosine similarity to each centroid.
- The nearest centroid wins.

**Why not use the LLM to classify intent?**
- Free (the embedding model is already loaded).
- Fast (~10ms vs ~500ms for an LLM call).
- Stable (no temperature non-determinism).
- Sufficient for 7 classes with clear prototypes.

**Why do we need intent classification at all?**
- To detect `correction` so we can persist the correction to long-term memory.
- To detect `commit_request` so we know to expect a refusal flow.
- To inform downstream behavior (e.g. `policy_question` → expect more SOP search).
- As an instrumentation signal in the dashboard.

**Where in the project?**
- `src/freight_copilot/memory/intent.py` — the classifier.
- Called at the start of every `AgentSession.stream_turn()`.

---

## 5.7 SQLite — long-term memory

**What is SQLite?**
A small, embedded relational database. Unlike Postgres or MySQL, there's no
server to run — SQLite is a single library that reads/writes one `.sqlite3`
file. It comes built into Python's standard library (`import sqlite3`).

**Why do we need long-term memory?**
LangGraph's `MemorySaver` keeps the message history within a single session
(in-memory, lost on exit). But we want the agent to remember things **across
sessions** — past triages of the same shipment, customer-specific quirks
("this customer is Platinum"), corrections from prior conversations.

That's a different scope: durable, structured, queryable by entity.

**Why SQLite specifically?**
- Stdlib — no install.
- One file (`data/memory.sqlite3`) — easy to backup, gitignore, reset.
- Indexed lookups — O(log n) recall by customer name or shipment ID.
- Trivial to inspect with any SQLite browser.
- Sufficient at our data volumes (<1000 rows).

**Why not Postgres?** Overkill.
**Why not just JSON files?** No indexed lookups; would degrade as data grows.
**Why not LangChain's built-in conversation memory?** Wrong abstraction —
those store conversation summaries, we want structured entity-keyed records.

**Schema (3 tables):**
```sql
customer_notes (id, ts, customer_name, note, source_thread_id)
shipment_notes (id, ts, shipment_id,    note, source_thread_id)
corrections    (id, ts, entity_kind, entity_id, correction, source_thread_id)
```

`source_thread_id` is the audit trail — every persisted fact links back to
the session that produced it.

**Where in the project?**
- `data/memory.sqlite3` (gitignored) — the actual db.
- `src/freight_copilot/memory/store.py` — schema + CRUD.
- `src/freight_copilot/memory/seed.py` — pre-populates with realistic
  historical notes for the 5 fixture customers/shipments.
- `src/freight_copilot/tools/recall.py` — the LLM-visible tools
  `recall_customer_history` and `recall_shipment_history` that read from it.

---

## 5.8 Pydantic — schema validation at the tool boundary

**What is Pydantic?**
A Python library for data validation. You define a class with type hints;
Pydantic auto-validates incoming data against those types and raises a
clear `ValidationError` if the shape is wrong.

```python
class ShipmentRecord(BaseModel):
    shipment_id: str
    carrier: str
    tracking_events: list[TrackingEvent]
    # ... etc
```

**Why do we need it?**
Each tool returns JSON to the LLM. If the JSON is malformed (missing field,
wrong type), the LLM doesn't know — it'll happily reason around the gap and
potentially hallucinate.

We catch this at the tool **boundary** by validating the return value
against a Pydantic model before handing it to the LLM. A malformed fixture
file fails loudly with `ValidationError`, not silently with bad agent
behavior.

This is a "fail loudly at the boundary" pattern: trust internal code,
validate at edges.

**Why specifically Pydantic v2?**
- The de facto standard in Python.
- Sub-millisecond validation overhead (Rust-backed in v2).
- `extra="allow"` lets fixtures carry forward-compat fields without breaking
  the model.
- LangChain itself uses Pydantic for its tool schemas, so we get
  compatibility.

**Where in the project?**
- `src/freight_copilot/tools/models.py` — `ShipmentRecord`, `LaneHistory`,
  `PortEvents`, and their `*NotFound` siblings.
- Each tool calls `Model.model_validate(raw)` before returning.

---

## 5.9 Streamlit — the web UI

**What is Streamlit?**
A Python framework for building web apps without writing HTML, CSS, or
JavaScript. You write a Python script that calls primitives like
`st.button("Click me")` and `st.markdown("# Hello")`; Streamlit serves the
script as a web page and re-runs it every time the user interacts.

**Why do we need a web UI?**
The IITM rubric requires a deployed app. The CLI is good for developers but
not for the demo. The web app makes the project clickable for a reviewer.

**Why Streamlit specifically?**
- **Native chat primitives** — `st.chat_message`, `st.chat_input` —
  perfect for our turn-based agent UX.
- **Native multi-page** — files in `pages/` become routable pages
  automatically.
- **Session state** — `st.session_state` persists across the script's
  re-runs.
- **Streaming-friendly** — `st.status` and `st.empty` let us update the UI
  as agent events arrive.
- **All Python** — no front-end build pipeline.

**Why not Gradio?**
Gradio is more "ML demo widget" oriented — great for "input box → output box"
demos, weaker on multi-page apps with shared state.

**Why not FastAPI + React?**
Vastly more code. We don't need a SPA-grade UI.

**Where in the project?**
- `app/streamlit_app.py` — Triage Console (entry page).
- `app/pages/1_📊_Monitoring.py` — KPIs, alerts, distributions.
- `app/pages/2_🔍_Sessions.py` — session browser + replay.
- `app/_helpers.py` — sys.path injection + small format helpers.

---

## 5.10 JSONL session logs — the single source of truth

**What is JSONL?**
"JSON Lines" — a file format convention where each line of the file is a
self-contained JSON object. So a JSONL file is just a text file with one
JSON object per line, e.g.:

```
{"ts": 1714..., "thread_id": "abc", "turn_index": 1, ...}
{"ts": 1714..., "thread_id": "abc", "turn_index": 2, ...}
```

**Why this format?**
- **Append-only writes are cheap** — no file rewrite.
- **Each line is self-contained** — parseable independently.
- **Easy to stream and tail.**
- **Trivial to ingest** — `for line in file: json.loads(line)`.

**What do we log?**
One line per agent turn (one `TurnRecord`):

```
{
  "ts": 1714...,
  "thread_id": "271e415bcfcb",
  "turn_index": 1,
  "user_input": "Triage shipment FRT-1042",
  "tool_calls": [{"name": "lookup_shipment", "args": {...}, "result_preview": "...", "duration_ms": 432}, ...],
  "final_response": "DIAGNOSIS\n…",
  "total_duration_ms": 22134,
  "input_tokens": 3138,
  "output_tokens": 1335,
  "model": "claude-haiku-4-5-20251001",
  "safety_findings": [],
  "intent": "triage_request",
  "intent_confidence": 0.71,
  "persona": "ops_associate",
  "error": null
}
```

**Why is this our single source of truth?**
The Streamlit Monitoring + Sessions pages read directly from these files —
no separate database, no parallel logging. The eval harness pulls token
usage from them. The CLI writes them. One format, many consumers.

**Where in the project?**
- `src/freight_copilot/session_logger.py` — the writer.
- `src/freight_copilot/monitoring.py` — the reader (used by the dashboards).
- `logs/session-<thread_id>.jsonl` — the actual files (gitignored).

---

## 5.11 LangSmith — distributed tracing (optional)

**What is LangSmith?**
A web service from the LangChain team that visualizes every LangGraph run
as a tree of LLM calls and tool calls. You can click into any LLM call and
see the full prompt, response, latency, token counts.

**Why optional?**
We already have JSONL logs locally. LangSmith adds a **debugging-grade
visualization** that's worth turning on when you can't tell why the agent
picked one tool over another.

**How to enable?**
Set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY=lsv2_...`,
`LANGCHAIN_PROJECT=freight-ops-copilot` in `.env`. LangChain auto-instruments.

---

## 5.12 pytest — the test framework

**What is pytest?**
The standard Python testing framework. You write functions starting with
`test_` and pytest runs them. Strong fixture system, clear failure output.

**Why do we need it?**
85 tests covering tools, RAG, memory, safety, personas, monitoring catch
regressions across all 8 phases. Without them, refactors get scary.

**What's the special discipline here?**
**No LLM calls in tests.** Every test is deterministic and free. Tests run
in seconds. This means we can run them on every change without paying.

**Where in the project?**
- `tests/` — 12 test files, 85 tests.
- `pyproject.toml` — `[tool.pytest.ini_options]` config.

---

## 5.13 ruff — lint + format

**What is ruff?**
A Python linter and formatter, written in Rust. Replaces black + isort +
flake8 + pylint with one tool that's 10–100× faster.

**Why one tool?**
Less config drift. One file (`pyproject.toml`) controls everything. One
command (`ruff check .` and `ruff format .`).

---

## 5.14 The supporting cast (one-liners)

| Library | What it does | Why |
|---|---|---|
| `python-dotenv` | Loads `.env` into env vars | Keeps API keys out of code/git |
| `pyyaml` | Parses YAML | Eval test specs are YAML for readability |
| `playwright` | Headless browser automation | Captures Streamlit screenshots (`chrome --headless --screenshot` doesn't work — Streamlit streams via WebSocket after load) |
| `loguru`, `tenacity`, `httpx` | Logging, retry, HTTP | In requirements; lightweight infra deps |
| `numpy` (pinned <2.0) | Math arrays | Used by intent classifier (cosine similarity); pinned because torch 2.2.2 macOS x86_64 was compiled against NumPy 1.x |
| `ragas`, `datasets` | Evaluation metrics (planned for Phase 9) | Faithfulness, answer relevance, context precision over RAG outputs |

---

# PART 6 — PUTTING IT ALL TOGETHER

If you remember nothing else:

| Layer | One-line takeaway |
|---|---|
| **Product** | Decision-support copilot for ops associates triaging shipment exceptions. Never commits actions. |
| **Personas** | Same agent, three framings (Tech / Finance / Customer). Safety rails constant. |
| **LLM** | Claude Haiku 4.5 via Anthropic API. Temperature 0. ~$0.01–$0.03 per turn. |
| **Agent runtime** | LangGraph ReAct loop. `MemorySaver` for in-session memory. Streaming events to UI. |
| **Tools** | 6 read-only tools — 3 data, 1 RAG, 2 memory. Pydantic-validated at the boundary. The absence of write-tools is the safety guarantee. |
| **RAG** | ChromaDB local + sentence-transformers all-MiniLM-L6-v2. 73 chunks across 9 SOPs. Cosine distance. |
| **Long-term memory** | SQLite, 3 tables (customer notes, shipment notes, corrections). Cross-session by design. |
| **Safety** | Output scanner — pattern regex + SOP-citation cross-check. Findings logged but don't block. |
| **UI** | Streamlit, 3 pages — Triage / Monitoring / Sessions. Read-only over JSONL logs. |
| **Logs** | One JSONL file per session. Single source of truth for every dashboard and the eval harness. |
| **Eval** | Deterministic predicate-based harness (acceptance + adversarial). 11/11 passing. RAGAs / multi-seed coming in Phase 9. |

The whole project, from the user's first click to the final response in
their browser, fits the same shape every time:

```
user → Streamlit → AgentSession → (intent classify → maybe persist correction →
LangGraph ReAct loop alternating LLM ↔ tools → safety scan → final →
write JSONL log) → Streamlit renders → user reads & decides → user takes the action
```

The mechanism is identical for ops_associate, finance_partner, and
customer_lead. The system prompt's persona addendum is what makes the
output land in the right shape for the role. Everything else — tools,
data, memory, safety, logging — is shared.
