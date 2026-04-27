# Phase 6 — Long-Term Memory, Intent Recognition, and Corrections

**Goal:** Move from "the agent forgets everything between sessions" to "the agent recognizes the user's intent, recalls prior triages and customer-specific quirks, and persists explicit corrections so the team never has to make the same fix twice."

## What's new vs. Phase 5

| Capability | Phase 3–5 | Phase 6 |
|---|---|---|
| Memory scope | Per-session (LangGraph `MemorySaver`, in-process) | Per-session **+ persistent across sessions** (SQLite) |
| User context | Whatever's in the current message history | Customer notes, shipment notes, explicit corrections from prior sessions |
| Intent recognition | None — every prompt treated the same | 7-class embedding-based classifier (~10ms, free) |
| Fix-up handling | Manual — repeat the correction every session | Automatic — `intent="correction"` → persist → recall |
| Tools available to LLM | 4 (P5) | **6** (`+ recall_customer_history`, `+ recall_shipment_history`) |

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  AgentSession.stream_turn(user_input)                            │
│                                                                  │
│  1. classify_intent(user_input) ──── 7-class centroid match      │
│     emit "intent" event                                          │
│                                                                  │
│  2. if intent == "correction":                                   │
│     persist Correction to SQLite under                           │
│     (entity_kind, entity_id) =                                   │
│        - shipment + FRT-XXXX if mentioned                        │
│        - customer + <name> if known customer matches             │
│        - general + thread_id otherwise                           │
│                                                                  │
│  3. LangGraph ReAct loop with 6 tools (Phase 5 + 2 new):         │
│       lookup_shipment, carrier_history, external_events,         │
│       search_sops, recall_shipment_history,                      │
│       recall_customer_history                                    │
│                                                                  │
│  4. Output safety scan (Phase 5)                                 │
│                                                                  │
│  5. _persist_turn_summary:                                       │
│     if a shipment ID was mentioned, write the first paragraph    │
│     of the response to shipment_notes (truncated, source_thread) │
│                                                                  │
│  6. Log turn record (now includes intent + intent_confidence)    │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                       data/memory.sqlite3
                       (shared across ALL sessions)
                       ├─ customer_notes
                       ├─ shipment_notes
                       └─ corrections
```

## Files added / changed

| File | Status | Purpose |
|---|---|---|
| [`src/freight_copilot/memory/store.py`](../src/freight_copilot/memory/store.py) | new | SQLite store: 3 tables, dataclass models, dataclass-backed CRUD |
| [`src/freight_copilot/memory/seed.py`](../src/freight_copilot/memory/seed.py) | new | Pre-populates the db with realistic historical notes for the 5 fixture customers/shipments |
| [`src/freight_copilot/memory/intent.py`](../src/freight_copilot/memory/intent.py) | new | Embedding-based 7-class intent classifier (uses the same `all-MiniLM-L6-v2` already loaded for RAG) |
| [`src/freight_copilot/tools/recall.py`](../src/freight_copilot/tools/recall.py) | new | `recall_customer_history` and `recall_shipment_history` tools for the agent |
| [`src/freight_copilot/agent.py`](../src/freight_copilot/agent.py) | updated | Classifies intent, persists corrections, writes turn summaries, exposes the 2 new tools |
| [`src/freight_copilot/prompts/system.py`](../src/freight_copilot/prompts/system.py) | updated | Teaches the agent: always check long-term memory; apply known corrections automatically |
| [`src/freight_copilot/__main__.py`](../src/freight_copilot/__main__.py) | updated | CLI now renders the classified intent inline |
| [`src/freight_copilot/session_logger.py`](../src/freight_copilot/session_logger.py) | updated | `TurnRecord` adds `intent` + `intent_confidence` fields |
| [`eval/run_cross_session_demo.py`](../eval/run_cross_session_demo.py) | new | The headline Phase 6 demo (Session A → correction → Session B reads it) |
| [`tests/test_memory_store.py`](../tests/test_memory_store.py) | new | 5 tests using a tempfile db (no clobbering production) |
| [`tests/test_intent_classifier.py`](../tests/test_intent_classifier.py) | new | 9 tests — 7 intent-routing parametrized + 2 invariants |
| [`tests/test_recall_tools.py`](../tests/test_recall_tools.py) | new | 4 tests against the seeded production db |

Test count: 40 → **58 passing**.

## SQLite schema

Three tables, one db file (`data/memory.sqlite3`), gitignored.

```sql
customer_notes (id, ts, customer_name, note, source_thread_id)
shipment_notes (id, ts, shipment_id, note, source_thread_id)
corrections    (id, ts, entity_kind, entity_id, correction, source_thread_id)
```

Indexes on the entity columns keep recall O(log n) even with thousands of notes. The `source_thread_id` is the audit trail — every persisted fact links back to the session that produced it.

## Intent classifier — 7 classes

| Intent | Examples | What the agent does |
|---|---|---|
| `triage_request` | "Triage FRT-1042" | Full diagnostic flow (Phase 2+ behavior) |
| `follow_up` | "What about the alternate?" | Continue with session memory; usually no fresh tool calls |
| `policy_question` | "What's our SOP for X?" | Heavy `search_sops` use, light data-tool use |
| `draft_request` | "Draft me an email" | Skip diagnosis, jump to draft using existing context |
| `correction` | "Actually it's Platinum, not Gold" | **Persist to SQLite**, then re-answer with the correction applied |
| `commit_request` | "Send the email for me" | Refusal flow (Phase 5 safety) |
| `meta` | "How do you work?" | Plain text answer; no tools |

The classifier uses cosine similarity to per-intent centroids built from 6 hand-curated prototype phrases each. Cost: **zero** ($0, ~10ms local inference).

## Cross-session demo — the headline result

`eval/run_cross_session_demo.py` runs **two separate `AgentSession` instances back-to-back** to prove memory persists across sessions.

### Session A (thread_id=271e415bcfcb)

Turn 1 — user asks for a triage on FRT-1042. Agent runs the standard flow.

Turn 2 — user says: *"Actually, Brookline Apparel got promoted to Platinum tier last week, not Gold. Update for any future triages."*

- ✅ Intent classifier: **`correction`** (conf=0.43, margin=0.19)
- ✅ Customer-name extractor finds "Brookline Apparel" matches a known customer
- ✅ Persisted to SQLite: `corrections(entity_kind='customer', entity_id='Brookline Apparel Co', correction=<verbatim>, source_thread_id=271e415bcfcb)`
- ✅ Agent's response in Turn 2: *"The correction is now recorded for all future triages of Brookline Apparel Co. ✓"*

### Session B (thread_id=571b96097d3d) — fresh process state, no in-memory link to Session A

Turn 1 — user asks: *"Looking at FRT-1042 again. Anything I should know about this customer?"*

- ✅ Agent calls `lookup_shipment(FRT-1042)` (the shipment record still says `tier="Gold"` — the static fixture isn't updated)
- ✅ Agent calls `recall_customer_history("Brookline Apparel Co")` — sees Session A's correction
- ✅ Response leads with: *"**IMPORTANT CORRECTION:** Brookline Apparel Co is **Platinum tier, not Gold** (per correction ts ..., source thread 271e415bcfcb). The shipment record still shows 'Gold' — you should treat them as Platinum for SLA and escalation purposes."*

The full trace is in [`docs/phase6-cross-session-trace.txt`](phase6-cross-session-trace.txt).

This demonstrates the three Phase 6 capabilities working together end-to-end:

1. **Intent classification** automatically detected the correction.
2. **Long-term memory** persisted it across separate `AgentSession` instances.
3. **Recall tools** surfaced it to a brand-new agent without being told to.

## What we learned the hard way

### 1. Detect-the-correction is necessary but not sufficient

The first version of `_persist_correction` correctly classified the user's input as a correction but persisted it under `entity_kind='general'` keyed on `thread_id`, because the input contained no `FRT-XXXX` shipment ID. Session B then couldn't find it (it queries by `entity_kind='customer'`).

Fix: extract the entity from the text. We now look up known customer names in the SQLite db (`SELECT DISTINCT customer_name FROM customer_notes UNION ...`) and substring-match against the input. This handles "Brookline Apparel got promoted..." even though the canonical record name is "Brookline Apparel Co".

### 2. Embedding-based intent is good enough — and cheap

A 7-class problem with hand-curated prototypes hits the right intent on every canonical phrasing in our test set (`tests/test_intent_classifier.py`). The lowest-margin case is `follow_up` vs `policy_question` (~0.05 margin) — those are genuinely close in meaning. We accept the ambiguity rather than over-engineer the classifier; the agent's downstream behavior degrades gracefully when intent is uncertain.

### 3. Don't let auto-summary write spam

`_persist_turn_summary` could pollute the db quickly if called on every turn. We:
- Only write when a shipment ID is present in the input or final response.
- Truncate to the first paragraph (typically the DIAGNOSIS line) at 400 chars.
- Skip empty responses (e.g., when the agent erred).

This keeps the per-shipment recall clean — readable summaries instead of full transcripts.

## Cost actuals (this phase)

| Item | Cost |
|---|---|
| Tests (no LLM calls, including 18 new) | $0.00 |
| Cross-session demo (3 LLM turns) | ~$0.04 |
| Smoke / dev iteration | ~$0.03 |
| **Phase 6 total** | **~$0.07** |
| Cumulative through Phase 6 | **~$0.69 / $20** budget (3.5%) |

## What this phase still does NOT do

| Gap | Filled by |
|---|---|
| Role / persona-based tone adaptation (B2B vs internal user) | Phase 7 |
| Web UI for human-in-the-loop demo | Phase 8 |
| RAGAs / LLM-as-judge metrics for memory recall quality | Phase 9 |
| Multi-seed eval runs across the cross-session flow | Phase 9 |
