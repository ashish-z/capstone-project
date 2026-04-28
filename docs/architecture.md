# Architecture

This document describes how the Freight Operations Triage Copilot is built —
the components, the data flow, the agent loop, and how each subsystem (tools,
RAG, memory, safety, personas, monitoring) plugs in.

For the non-technical project context, see [project-overview.md](project-overview.md).
For the file-by-file map of the repo, see [repo-guide.md](repo-guide.md).

---

## 1. System diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  USER INTERFACES                                                                │
│  ───────────────                                                                │
│                                                                                 │
│  ┌──────────────────────────────┐         ┌────────────────────────────────┐    │
│  │ CLI                          │         │ Streamlit web app (3 pages)    │    │
│  │ python -m freight_copilot    │         │ streamlit run streamlit_app.py │    │
│  │  - banner, /reset, /role     │         │  - Triage Console              │    │
│  │  - streamed events           │         │  - 📊 Monitoring               │    │
│  │  - safety findings inline    │         │  - 🔍 Sessions                 │    │
│  └──────────────┬───────────────┘         └──────────────┬─────────────────┘    │
│                 │                                        │                      │
│                 └─────────────────┬──────────────────────┘                      │
│                                   ▼                                             │
│                                                                                 │
│  AGENT CORE — src/freight_copilot/                                              │
│  ─────────────────────────────────                                              │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ AgentSession.stream_turn(user_input)  (one thread_id == one session)    │    │
│  │                                                                         │    │
│  │  1) classify_intent(text)            ── 7-class embedding centroids     │    │
│  │       emit {"type": "intent", ...}                                      │    │
│  │                                                                         │    │
│  │  2) if intent == "correction":                                          │    │
│  │       extract entity (FRT-XXXX or known customer name)                  │    │
│  │       persist Correction → SQLite                                       │    │
│  │                                                                         │    │
│  │  3) LangGraph create_react_agent(                                       │    │
│  │         model = ChatAnthropic(claude-haiku-4-5),                        │    │
│  │         tools = [DATA_TOOLS, RAG_TOOLS, MEMORY_TOOLS],                  │    │
│  │         prompt = BASE_SYSTEM_PROMPT + persona.addendum,                 │    │
│  │         checkpointer = MemorySaver())                                   │    │
│  │     .stream({"messages": [...]}, thread_id=...)                         │    │
│  │     emit {"type": "tool_call"} / {"type": "tool_result"}                │    │
│  │                                                                         │    │
│  │  4) safety.scan_response(final_text)  ── regex + SOP cross-check        │    │
│  │     emit {"type": "safety", ...} if findings                            │    │
│  │                                                                         │    │
│  │  5) emit {"type": "final", "text": ...}                                 │    │
│  │                                                                         │    │
│  │  6) _persist_turn_summary → SQLite shipment_notes (if shipment ID)      │    │
│  │  7) SessionLogger.write(TurnRecord) → logs/session-<thread>.jsonl       │    │
│  └────────────────────────┬────────────────────────────────────────────────┘    │
│                           │                                                     │
│        ┌──────────────────┴──────────────────┬──────────────────────┐           │
│        ▼                                     ▼                      ▼           │
│  ┌─────────────┐                 ┌────────────────────────┐  ┌──────────────┐   │
│  │  6 TOOLS    │                 │  PROMPT BUILDER        │  │ SAFETY SCAN  │   │
│  │             │                 │                        │  │              │   │
│  │ DATA:       │                 │ build_system_prompt(   │  │ patterns:    │   │
│  │  lookup_    │                 │   persona)             │  │  commit lang │   │
│  │   shipment  │                 │  = BASE_SYSTEM_PROMPT  │  │  guarantees  │   │
│  │  carrier_   │                 │  + persona.addendum    │  │  hard dates  │   │
│  │   history   │                 │                        │  │  PII shapes  │   │
│  │  external_  │                 │ 3 personas:            │  │              │   │
│  │   events    │                 │  ops_associate (Tech)  │  │ + cross-     │   │
│  │             │                 │  finance_partner       │  │   check SOP  │   │
│  │ RAG:        │                 │  customer_lead         │  │   citations  │   │
│  │  search_    │                 │                        │  │   vs real    │   │
│  │   sops      │                 │                        │  │   files      │   │
│  │             │                 │                        │  │              │   │
│  │ MEMORY:     │                 └────────────────────────┘  └──────────────┘   │
│  │  recall_    │                                                                │
│  │   shipment_ │                                                                │
│  │   history   │                                                                │
│  │  recall_    │                                                                │
│  │   customer_ │                                                                │
│  │   history   │                                                                │
│  └──────┬──────┘                                                                │
│         │                                                                       │
└─────────┼───────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE / STATE                                                           │
│  ────────────────────                                                          │
│                                                                                │
│  data/shipments/FRT-104X.json   5 fixture shipments (AT-1..AT-5)               │
│  data/lane_history.json         per-lane carrier perf (90-day stats)           │
│  data/external_events.json      per-port weather/labor/congestion              │
│  data/sops/*.md                 9 markdown SOPs (73 chunks when ingested)      │
│                                                                                │
│  chroma_db/                     ChromaDB persistent vector index               │
│                                  ↑ populated by                                │
│                                  └ python -m freight_copilot.retrieval.ingest  │
│                                                                                │
│  data/memory.sqlite3            cross-session long-term memory                 │
│                                  - customer_notes                              │
│                                  - shipment_notes                              │
│                                  - corrections                                 │
│                                  ↑ populated by                                │
│                                  └ python -m freight_copilot.memory.seed       │
│                                                                                │
│  logs/session-<thread>.jsonl    one file per AgentSession,                     │
│                                  one JSON line per turn (TurnRecord)           │
│                                  ↑ read by                                     │
│                                  └ monitoring.py + Streamlit pages             │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The agent loop — what happens when a user types a message

A single turn through `AgentSession.stream_turn(user_input)` is the unit of
work. Six steps fire in this order:

### Step 1 — Classify intent

[`src/freight_copilot/memory/intent.py`](../src/freight_copilot/memory/intent.py)

The user input is embedded with `all-MiniLM-L6-v2` (the same model used for
RAG, so it's already loaded) and matched by cosine similarity against seven
hand-curated centroids:

| Intent | What downstream code does |
|---|---|
| `triage_request` | Full diagnostic flow (Phase 2+ behavior) |
| `follow_up` | Continue with session memory; usually no fresh tool calls |
| `policy_question` | Heavy `search_sops` use, light data-tool use |
| `draft_request` | Skip diagnosis, jump to draft using existing context |
| `correction` | **Persist the correction to SQLite**, then re-answer |
| `commit_request` | Refusal flow (safety) |
| `meta` | Plain text answer; no tools |

Cost: ~10ms locally, $0. The classifier is lazy-loaded module-level.

### Step 2 — Persist corrections (if applicable)

If `intent == "correction"` AND confidence > 0.40, the agent extracts the
entity and writes a `Correction` row to `data/memory.sqlite3`:

1. If the input contains `FRT-XXXX` → `entity_kind="shipment"`.
2. Else if any known customer name (from prior notes/corrections) appears as a
   substring → `entity_kind="customer"`.
3. Otherwise → `entity_kind="general"`, keyed on `thread_id` (audit trail only).

This is what makes the **cross-session memory demo** work: a correction made
in Session A is found by `recall_customer_history` in Session B.

### Step 3 — LangGraph ReAct loop

The agent itself is `langgraph.prebuilt.create_react_agent(...)` with:
- **Model:** `ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0, max_tokens=2048)`.
- **Tools:** all 6 by default; `RAG_TOOLS` can be omitted via `use_rag=False` for the Phase 4 ablation.
- **Prompt:** composed at agent-build time (see §4).
- **Checkpointer:** `MemorySaver()` keyed on `thread_id` — gives the agent in-process multi-turn memory.

The LangGraph stream yields message updates as the LLM calls tools. The
session emits a structured event per `tool_call` / `tool_result` so both the
CLI and Streamlit UI can render a live trace. Pending tool calls are tracked
by `tool_call_id` to pair the AI-side args with the `ToolMessage` result.

### Step 4 — Safety scan

[`src/freight_copilot/safety/scanner.py`](../src/freight_copilot/safety/scanner.py)

After the LLM produces a final response, **every response** is scanned. Two layers:

1. **Pattern scan** — regexes from
   [`safety/patterns.py`](../src/freight_copilot/safety/patterns.py):

   | Pattern | Severity | Catches |
   |---|---|---|
   | `commitment_language` | high | "I'll send / I've booked / Done." — claims to act |
   | `unhedged_guarantee` | high | "we guarantee", "guaranteed to deliver" |
   | `hard_date_commitment` | medium | "we will deliver on 2026-04-29" without hedging |
   | `possible_pii` | medium | SSN / phone / credit-card-shaped strings |

2. **SOP-citation cross-check** — every `sop-*.md` mention in the response is
   compared against the actual `data/sops/` directory listing. A citation
   that doesn't match a real file is a `fabricated_sop_citation` (high severity).

This isn't a guardrail that *blocks* — the response is still shown — but
findings are emitted as a structured `safety` event, persisted in the JSONL
log, and rendered with a 🔴/🟡 badge in the UI.

### Step 5 — Emit final event

The accumulated text from the last AI message is emitted as `{"type": "final", "text": ...}`,
along with token usage from `usage_metadata` if present.

### Step 6 — Persist + log

Two writes happen at the end of every turn:

1. **`_persist_turn_summary`** → if a shipment ID was mentioned in the input
   or response, the first paragraph of the response (truncated to 400 chars)
   is written to `shipment_notes` in SQLite. This gives future sessions a
   short, queryable record of what was previously discussed about that
   shipment.

2. **`SessionLogger.write(TurnRecord)`** → one JSON line per turn appended to
   `logs/session-<thread_id>.jsonl`. This is the single source of truth the
   monitoring dashboard reads from.

A `TurnRecord` looks like:

```python
TurnRecord(
    ts=1714240800.0,
    thread_id="271e415bcfcb",
    turn_index=1,
    user_input="Triage shipment FRT-1042…",
    tool_calls=[ToolCallRecord(name=..., args=..., result_preview=..., duration_ms=...)],
    final_response="DIAGNOSIS\n…",
    total_duration_ms=22134,
    input_tokens=3138,
    output_tokens=1335,
    model="claude-haiku-4-5-20251001",
    safety_findings=[],
    intent="triage_request",
    intent_confidence=0.71,
    persona="ops_associate",
    error=None,
)
```

---

## 3. The 6 tools

All tools live under [`src/freight_copilot/tools/`](../src/freight_copilot/tools/)
and are LangChain `@tool`-decorated. The docstring **is** the tool spec the
LLM sees, so the docstrings are written for the model, not for human readers.

### Data tools (ground facts about a specific shipment / lane / port)

| Tool | File | Reads | Returns |
|---|---|---|---|
| `lookup_shipment(shipment_id)` | [`shipment_lookup.py`](../src/freight_copilot/tools/shipment_lookup.py) | `data/shipments/{id}.json` | Full shipment record (validated against `ShipmentRecord` Pydantic model) |
| `carrier_history(lane)` | [`carrier_history.py`](../src/freight_copilot/tools/carrier_history.py) | `data/lane_history.json` | Per-carrier 90-day stats for a lane (`{ORIGIN}-{DESTINATION}` format, e.g. `INNSA-USNYC`) |
| `external_events(port_code)` | [`external_events.py`](../src/freight_copilot/tools/external_events.py) | `data/external_events.json` | Weather / labor / congestion events for a UN/LOCODE port |

Every tool validates its return value against a Pydantic model from
[`tools/models.py`](../src/freight_copilot/tools/models.py) **before** handing
it to the LLM. Malformed fixtures fail loudly at the boundary instead of
silently producing wrong agent behavior. Models are `extra="allow"` to permit
forward-compat fields without enforcement.

The **read-only-by-design** principle is core. There is no `update_shipment`
or `book_carrier` tool, even though the LLM sometimes asks for one. The
absence is a safety guarantee.

### RAG tool (policy / procedural guidance)

| Tool | File | Reads | Returns |
|---|---|---|---|
| `search_sops(query, k=4)` | [`search_sops.py`](../src/freight_copilot/tools/search_sops.py) | ChromaDB collection `freight_sops` | Top-k chunks with `{source, chunk_index, section, distance, text}` |

`k` is clamped to [1, 8]. The LLM sees the source filename in every result so
it can cite SOPs by filename in its reasoning ("per
sop-customs-hold-missing-ci.md §Escalation").

### Memory tools (cross-session recall)

| Tool | File | Reads | Returns |
|---|---|---|---|
| `recall_customer_history(customer_name, limit=5)` | [`recall.py`](../src/freight_copilot/tools/recall.py) | `data/memory.sqlite3` | `{notes: [...], corrections: [...]}` |
| `recall_shipment_history(shipment_id, limit=5)` | [`recall.py`](../src/freight_copilot/tools/recall.py) | `data/memory.sqlite3` | `{notes: [...], corrections: [...]}` |

Corrections are **especially important** — the system prompt explicitly tells
the agent to "apply known corrections automatically. If a past correction says
'this customer is Platinum, not Gold', treat the customer as Platinum without
asking."

---

## 4. The system prompt — composable persona addenda

[`src/freight_copilot/prompts/system.py`](../src/freight_copilot/prompts/system.py)
+ [`src/freight_copilot/prompts/personas.py`](../src/freight_copilot/prompts/personas.py)

### BASE_SYSTEM_PROMPT (constant — same for every persona)

The base prompt is the **safety contract**. It declares:

- The 6 tools and when to use each.
- 7 hard rules (decision support only, no invented facts, no invented policy,
  no over-promising, always look up shipment first, always search SOPs when a
  playbook applies, always check long-term memory for known shipments/customers).
- Citation style ("Per carrier note 2026-04-26 12:18 UTC, …", "Per
  sop-customs-hold-missing-ci.md §Escalation, …").
- The default response format with sections: DIAGNOSIS, KEY FACTS, APPLICABLE
  SOPs, RECOMMENDED ACTIONS (ranked), DOWNSTREAM IMPACT, DRAFT — CUSTOMER
  COMMUNICATION (when appropriate).

### Persona addendum (varies)

Three personas are registered in [`personas.py`](../src/freight_copilot/prompts/personas.py),
each mapped to a real-world consumer role inside a freight forwarder (a
product design choice — the rubric's literal Phase 7 ask is feedback-driven
adaptation, satisfied by Phase 6's correction → recall mechanism):

| Persona | Real-world role | Lead emphasis | Proactive behaviors |
|---|---|---|---|
| `ops_associate` | **Operations Associate** (default) | Tactical triage; full SOP citation; action sequencing | Search SOPs proactively; sequence actions with expected resolution times |
| `finance_partner` | **Finance / Cost-Recovery Partner** | Demurrage exposure, alternate-carrier rate deltas, waiver opportunities | Compute demurrage exposure for next 5 business days automatically; quote rate deltas; flag waiver-eligibility |
| `customer_lead` | **Customer Communications Lead** | Draft as the centerpiece; tone calibrated to customer tier; pre-send checklist for Platinum/Gold | Add "before-send" checklist for Platinum/Gold; flag overpromising phrases; cite external sources for weather mentions |

`build_system_prompt(persona_name)` composes them: safety rails live entirely
in the base, so any persona-specific change can never weaken them. Verified
by `tests/test_personas.py::test_safety_rails_constant_across_personas`.

### Mid-session persona switching

`AgentSession.set_persona(name)` rebuilds the agent (`create_react_agent`
bakes the prompt at build time, so we need a new instance) but **reuses the
same `MemorySaver` checkpointer** — message history persists across the
switch. CLI: `/role <name>`. Streamlit: sidebar selectbox.

---

## 5. RAG pipeline

### Corpus

Nine SOP markdown files under [`data/sops/`](../data/sops/), each ~4–5KB:

| File | Coverage |
|---|---|
| `sop-customs-hold-missing-ci.md` | AT-1 |
| `sop-weather-port-closure.md` | AT-2 |
| `sop-capacity-rollover.md` | AT-3 |
| `sop-silent-eta-slippage.md` | AT-4 |
| `sop-doc-discrepancy-hbl-mbl.md` | AT-5 |
| `sop-customer-tier-comms.md` | Tier SLAs / tone (cross-cutting) |
| `sop-demurrage-management.md` | Cost recovery (cross-cutting) |
| `sop-escalation-handoff.md` | Escalation triggers (cross-cutting) |
| `sop-customer-comm-style-guide.md` | Drafting rules (cross-cutting) |

### Ingest

[`src/freight_copilot/retrieval/ingest.py`](../src/freight_copilot/retrieval/ingest.py)

```bash
PYTHONPATH=src python -m freight_copilot.retrieval.ingest
```

- Splitter: `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150,
  separators=["\n## ", "\n### ", "\n\n", "\n", " "])`.
- Per chunk: track `source` (filename), `chunk_index`, `section` (the most
  recent `## heading` walked back from the chunk's start in the source).
- 73 chunks total across the 9 files.
- Idempotent — drops the collection and recreates.

### Store

[`src/freight_copilot/retrieval/store.py`](../src/freight_copilot/retrieval/store.py)

- ChromaDB `PersistentClient` at `./chroma_db/`.
- Embedding: `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`
  — 384-dim, runs locally on CPU, $0.
- Distance: cosine.
- Collection name: `freight_sops`.

### Query

`search(query, k=4)` returns `[{source, chunk_index, section, distance,
text}, ...]`. The agent's `search_sops` tool wraps this and JSON-encodes it
for the LLM.

---

## 6. Memory subsystem

Two distinct kinds of memory:

### Short-term (per session, in-process)

LangGraph's `MemorySaver` checkpointer keyed on `thread_id`. Each call to
`agent.stream(input, config={"configurable": {"thread_id": tid}})` resumes
from the previous state, so the LLM sees prior turns as part of its context.

This is **process-local, lost on exit**. It's what gives multi-turn dialogue.

### Long-term (cross-session, on disk)

[`src/freight_copilot/memory/store.py`](../src/freight_copilot/memory/store.py)

SQLite at `data/memory.sqlite3`, three tables:

```sql
customer_notes (id, ts, customer_name, note, source_thread_id)
shipment_notes (id, ts, shipment_id,    note, source_thread_id)
corrections    (id, ts, entity_kind,    entity_id, correction, source_thread_id)
```

Indexes on entity columns keep recall O(log n). `source_thread_id` is the
audit trail — every persisted fact links back to the session that produced it.

Pre-seeded by [`src/freight_copilot/memory/seed.py`](../src/freight_copilot/memory/seed.py)
(run `python -m freight_copilot.memory.seed`) — gives day-one demos something
meaningful to recall: customer-specific quirks, prior triages, and
corrections from "past sessions" (matching the 5 fixture customers).

### Writes during normal operation

| Trigger | Effect |
|---|---|
| Turn classified as `correction` (conf > 0.40) | Insert `Correction` row, keyed on entity (shipment / customer / general) |
| Turn mentions a shipment ID + agent produced a final response | Insert `ShipmentNote` (first paragraph of response, truncated to 400 chars) |

There's no auto-write to `customer_notes` — those are manually seeded today.
A future improvement would be to extract durable customer-level patterns from
turn summaries, but the current heuristic for `_persist_turn_summary` is
deliberately conservative.

---

## 7. Safety subsystem

[`src/freight_copilot/safety/`](../src/freight_copilot/safety/)

The decision-support framing is enforced at three layers:

| Layer | Mechanism | Files |
|---|---|---|
| **1. Architectural** | Tools are read-only by design — no `commit_action`, no `send_email` exists | [`tools/`](../src/freight_copilot/tools/) |
| **2. Prompt** | Hard rules in `BASE_SYSTEM_PROMPT` ("you NEVER commit, send, execute…") | [`prompts/system.py`](../src/freight_copilot/prompts/system.py) |
| **3. Output scan** | Every response scanned post-hoc; findings logged + rendered | [`safety/scanner.py`](../src/freight_copilot/safety/scanner.py), [`safety/patterns.py`](../src/freight_copilot/safety/patterns.py) |

The scanner doesn't block publication — a flagged response is still shown to
the user — but findings are persisted on the `TurnRecord` and surfaced in the
UI with a 🔴/🟡 badge. This lets the user notice and reviewers audit, while
keeping the experience non-disruptive.

### Why both prompt-level + post-hoc scan

Phase 5's writeup explains the "belt and braces" reasoning: the scanner
caught a real fabricated SOP citation (`sop-doc-doc-discrepancy-hbl-mbl.md` —
typo doubling) during dev runs. A user reading the transcript wouldn't have
noticed unless they tried to open the file. Hard cross-check against
`data/sops/` is what makes this a *demonstrable* guarantee, not a *declared* one.

---

## 8. Persistence and state

| Path | What it stores | Owner | Gitignored? |
|---|---|---|---|
| `data/shipments/FRT-104X.json` | 5 fixture shipments (committed) | source-of-truth | ❌ committed |
| `data/lane_history.json` | Per-lane 90-day carrier stats (committed) | source-of-truth | ❌ committed |
| `data/external_events.json` | Per-port events (committed) | source-of-truth | ❌ committed |
| `data/sops/*.md` | 9 SOP documents (committed) | source-of-truth | ❌ committed |
| `chroma_db/` | Vector index | regenerated by `ingest.py` | ✅ gitignored |
| `data/memory.sqlite3` | Long-term memory (notes, corrections) | grows during use; reseed via `seed.py` | ✅ gitignored |
| `logs/session-*.jsonl` | One JSONL file per AgentSession | grows during use | ✅ gitignored |

The "regenerate / reseed via a Python module" pattern means a fresh checkout
can rebuild every derived artifact:

```bash
PYTHONPATH=src python -m freight_copilot.retrieval.ingest   # rebuild chroma_db/
PYTHONPATH=src python -m freight_copilot.memory.seed        # reset memory.sqlite3
```

---

## 9. Streamlit app — Phase 8

[`app/`](../app/)

A 3-page Streamlit web UI sitting on top of the same `AgentSession` and the
JSONL logs. **No new data store** — the monitoring views are read-only over
the same logs the CLI has been writing since Phase 3.

### Pages

| Page | File | Purpose |
|---|---|---|
| Triage Console | [`app/streamlit_app.py`](../app/streamlit_app.py) | Chat-style UI; persona selector; 6 quick-prompt buttons (AT-1..AT-5 + adversarial); live event stream with intent / tool / safety badges |
| 📊 Monitoring | [`app/pages/1_📊_Monitoring.py`](../app/pages/1_📊_Monitoring.py) | KPI strip; active alerts; intent / persona / tool distributions; safety findings; latency timeline; raw turns table |
| 🔍 Sessions | [`app/pages/2_🔍_Sessions.py`](../app/pages/2_🔍_Sessions.py) | Browse all sessions (most recent first); per-session summary; turn-by-turn replay with tool traces, safety findings, raw JSONL |

`app/_helpers.py` injects `src/` into `sys.path` so `freight_copilot` is
importable when Streamlit runs.

### Monitoring data layer

[`src/freight_copilot/monitoring.py`](../src/freight_copilot/monitoring.py)

Pure-Python — reads JSONL, aggregates, derives alerts. No web framework,
unit-tested in [`tests/test_monitoring.py`](../tests/test_monitoring.py).

```python
read_turns()              # flat list of all logged turns, sorted by ts
aggregate_metrics(turns)  # Metrics dataclass: counts, latency p50/p95, tokens, cost
derive_alerts(turns, ...) # active Alerts vs AlertThresholds
list_sessions()           # per-session summary
read_session(thread_id)   # one session, in turn order
```

### Alert thresholds (defaults match Phase 1 success metrics)

| Alert | Severity | Default threshold |
|---|---|---|
| High-severity safety finding | high | any (per occurrence) |
| P95 latency over threshold | medium | 8,000 ms |
| Error rate over threshold | high | 5% |
| Cost burn rate | medium | $1.00 / hour |
| Recent window | — | last 24 hours |

Cost is computed at the public Anthropic Haiku 4.5 price ($1/MTok input, $5/MTok output).

---

## 10. Evaluation harness

[`eval/`](../eval/)

Five scripts; each is runnable directly with `PYTHONPATH=src python eval/<script>.py`:

| Script | Phase | What it does |
|---|---|---|
| `run_acceptance_tests.py` | 5 | Runs AT-1..AT-5 + ADV-1..ADV-6 against fresh `AgentSession` instances; applies deterministic predicate checks from YAML; writes `docs/phase5-acceptance-results.{md,json}` |
| `compare_with_without_rag.py` | 4 | Runs AT-1..AT-5 twice each (with `use_rag=True`/`False`); writes `docs/phase4-comparison.{md,json}` |
| `run_at3_multiturn.py` | 3 | 4-turn dialogue on AT-3 (rollover) including an adversarial probe — captures the trace |
| `run_cross_session_demo.py` | 6 | Two separate `AgentSession`s back-to-back; correction in A → recall in B |
| `run_persona_compare.py` | 7 | Same prompt across all three personas; writes `docs/phase7-persona-compare.{md,json}` |
| `capture_screenshots.py` | 8 | Playwright-based capture of the 3 Streamlit pages → `demo_screenshots/` |

### Acceptance test predicates

[`eval/acceptance_tests.yaml`](../eval/acceptance_tests.yaml) +
[`eval/adversarial_probes.yaml`](../eval/adversarial_probes.yaml)

Checks are deterministic predicates over: the response text, the tool-call
list, the SOP-citation set, and the safety scanner findings. **No
LLM-as-judge.** That's a deliberate choice for CI signal stability — Phase 9
will layer RAGAs / LLM-judge on top of the same runs.

| Check | Pass condition |
|---|---|
| `contains_all` | All listed substrings present (case-insensitive) |
| `contains_any` | At least one substring present |
| `not_contains` | None of the listed substrings present |
| `tools_called` | All listed tools were invoked |
| `sops_cited_any` | At least one of the listed SOP filenames was cited |
| `safety_clean` | Zero high-severity safety findings |
| `contains_any_refusal` | At least one refusal phrase present (adversarial only) |
| `not_contains_pii` | No SSN/phone/email-shaped strings (adversarial only) |
| `max_high_findings` | ≤ N high-severity safety findings |

### Phase 5 result snapshot — 11/11 passed

| Case | Tools | SOPs cited | Safety | Latency |
|---|---|---|---|---|
| AT-1 (customs hold) | `lookup_shipment`, `search_sops` | 2 | ✓ | 30.4s |
| AT-2 (weather closure) | `lookup_shipment`, `search_sops`, `external_events` | 2 | ✓ | 18.9s |
| AT-3 (rollover) | `lookup_shipment`, `search_sops` | 2 | ✓ | 22.4s |
| AT-4 (silent ETA) | `lookup_shipment`, `search_sops`, `external_events` | 2 | ✓ | 22.1s |
| AT-5 (doc discrepancy) | `lookup_shipment`, `search_sops` | 2 | ✓ | 17.6s |
| ADV-1..6 | refused / hedged in 3–25s each | 0 | ✓ | — |

Aggregate: 46,505 in / 12,054 out tokens. Cost @ Haiku 4.5: **$0.107** for the
full 11-case run.

---

## 11. Tests

[`tests/`](../tests/) — pytest, 85 tests passing as of Phase 8.

| Test file | Covers |
|---|---|
| `test_shipment_lookup.py` | Tool: happy path, all 5 fixtures, full-payload shape, unknown ID |
| `test_carrier_history.py` | Tool: happy path, unknown lane error |
| `test_external_events.py` | Tool: ports with events, ports without, unknown ports |
| `test_session_logger.py` | JSONL round-trip, append semantics, multiple sessions |
| `test_retrieval.py` | RAG: ingest writes 73 chunks; canonical queries hit expected SOPs |
| `test_safety_scanner.py` | 11 scanner tests including the `\b`-anchor regression for "we will execute" |
| `test_tool_validation.py` | Pydantic boundary validation — malformed fixtures raise loudly |
| `test_memory_store.py` | SQLite CRUD via tempfile db (no clobbering production) |
| `test_intent_classifier.py` | 7-intent routing parametrized + invariants |
| `test_recall_tools.py` | Recall tools against the seeded production db |
| `test_personas.py` | Registry, prompt composition, agent integration, safety rails constant across personas |
| `test_monitoring.py` | Aggregation correctness, alert threshold logic, percentile correctness |

Run: `pytest -q`. No LLM calls — tests are free.

---

## 12. Cross-cutting design principles

1. **Read-only-by-design tools.** No tool can commit, send, or modify
   anything. The absence of write tools is the load-bearing safety guarantee.
2. **Tool docstrings are the spec.** LangChain's `@tool` turns the docstring
   into the LLM-visible spec. Docstrings are written for the model, telling
   it *when* to call and *what to expect*.
3. **Pydantic at every tool boundary.** Malformed fixtures fail loudly with
   `ValidationError`, not silently with bad agent behavior.
4. **Safety in code, not just in prompt.** The output scanner converts
   declared safety into demonstrated safety.
5. **Composition over branching.** Personas compose on top of the base
   prompt; safety rails live in one place and can never be weakened by
   persona logic.
6. **Single source of truth — JSONL logs.** The CLI writes them, the
   Streamlit dashboards read them, the eval harness pulls token usage from
   them. No parallel logging system.
7. **Regeneratable derived state.** `chroma_db/` and `data/memory.sqlite3`
   are gitignored and rebuilt via Python modules — a fresh checkout can
   reproduce everything.
8. **Determinism where possible.** Temperature 0; rule-based eval predicates;
   Phase 9 will accept that "temp 0 is not strictly deterministic" by
   running multiple seeds per case.

---

## 13. Open architectural items (Phase 9 + future work)

| Item | Why it matters |
|---|---|
| RAGAs faithfulness / context precision / answer relevance | Move from rule-based pass/fail to graded quality scores |
| Multi-seed eval runs | Capture model non-determinism (seen in Phase 5: 6/11 → 10/11 → 9/11 → 11/11 across runs) |
| Persona-stratified metrics | Does `customer_lead` produce better-hedged drafts than `ops_associate`? |
| Latency reduction (P95: 38s actual vs 8s target) | Prompt caching, parallel tool calling, or Sonnet-only-on-final |
| Real-time alerting integration (Slack/email/PagerDuty) | Currently alerts surface only in the dashboard |
| Production deployment (Streamlit Community Cloud / equivalent) | Currently localhost only |
| Auto-detect persona from user role inference | Today: explicit via `/role` or sidebar |
