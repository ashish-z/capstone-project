# Repository Guide — File-by-File

A walking tour of every file and directory. For the architectural overview,
see [architecture.md](architecture.md).

---

## Top level

```
.
├── app/                       Streamlit demo (Phase 8)
├── data/                      Mock fixtures + RAG corpus + (gitignored) memory db
├── demo_screenshots/          Captured screenshots for submission
├── docs/                      Phase docs + this file + the new top-level docs
├── eval/                      Acceptance tests + adversarial probes + harnesses
├── logs/                      JSONL session logs (gitignored)
├── src/freight_copilot/       The agent package
├── tests/                     pytest suite
├── .env.example               Env var template (copy to .env)
├── .gitignore                 Ignores logs/, chroma_db/, memory.sqlite3, .venv/, .env
├── LICENSE                    MIT
├── README.md                  Quickstart + status table
├── pyproject.toml             ruff config + project metadata
├── requirements.txt           Pinned dependencies
└── Capstone-Project-...pdf    IITM assignment brief (background reference only)
```

---

## `src/freight_copilot/` — the agent package

```
src/freight_copilot/
├── __init__.py                Package marker — exposes __version__
├── __main__.py                CLI entry point: `python -m freight_copilot`
├── agent.py                   AgentSession + build_agent — the runtime
├── monitoring.py              Pure-Python data layer for the dashboards
├── session_logger.py          JSONL writer; TurnRecord/ToolCallRecord/SafetyFindingRecord dataclasses
├── memory/                    Long-term + short-term memory
├── prompts/                   System prompt + persona registry
├── retrieval/                 RAG ingest + vector store
├── safety/                    Output safety scanner + patterns
└── tools/                     LangChain @tool definitions for the agent
```

### `agent.py`
The heart of the runtime. Defines:
- `build_agent(model, checkpointer, use_rag, persona)` — builds a fresh
  LangGraph ReAct agent with the right tools and the persona-composed prompt.
- `AgentSession` — wraps the agent + a `MemorySaver` checkpointer + a
  `SessionLogger`. One AgentSession == one `thread_id` == one JSONL log file.
  - `.stream_turn(user_input)` — runs one turn, yielding structured events
    (`intent` → `tool_call` → `tool_result` → `safety` → `final`).
  - `.set_persona(name)` — switch persona mid-session (rebuilds agent, keeps
    checkpointer so message history persists).
  - `_persist_correction()` — handles the Phase 6 correction → SQLite path.
  - `_persist_turn_summary()` — auto-writes a brief shipment note when the
    turn references a shipment ID.
- `run_once(user_input)` — one-shot helper for tests/scripts.

### `__main__.py`
The CLI. `python -m freight_copilot` opens an interactive loop:
- Banner + persona list at startup.
- Reads input line-by-line, calls `session.stream_turn()`, prints structured
  events inline (`[intent] / [tool→] / [tool←] / [safety] / final`).
- Slash commands: `/reset` (new session, same persona), `/role <name>`
  (switch persona), `/role` alone (lists personas).
- Top-level exception handler so a tool crash doesn't kill the loop.

### `session_logger.py`
The JSONL writer. Three dataclasses:
- `TurnRecord` — one logical turn (input + tool calls + final + safety + tokens + latency + intent + persona).
- `ToolCallRecord` — name, args, truncated result preview, duration.
- `SafetyFindingRecord` — pattern_name, severity, matched_text.

`SessionLogger(thread_id)` opens `logs/session-<thread_id>.jsonl` for append.
One JSON line per `write(TurnRecord)`. `now_ms()` helper for monotonic
timestamps.

### `monitoring.py`
Pure Python, no Streamlit. The data layer the dashboard pages call into.
- `read_turns()` — flat list of all logged turns across all session files,
  sorted by ts.
- `aggregate_metrics(turns)` → `Metrics` dataclass (n_turns, n_sessions,
  n_errors, latency p50/p95/avg, tokens in/out, cost, intent counts, persona
  counts, tool counts, safety counts by severity + pattern).
- `derive_alerts(turns, AlertThresholds(...))` → list of `Alert`s. Defaults
  match Phase 1 success metrics (P95 < 8s, error rate < 5%, cost < $1/h).
- `list_sessions()` — per-session summary (turns, persona, model, ts range,
  safety/error flags).
- `read_session(thread_id)` — one session, in turn order.

Cost computed at the public Anthropic Haiku 4.5 prices: `(1.0, 5.0)` USD / MTok.

---

### `src/freight_copilot/tools/`

LangChain `@tool`-decorated functions. Docstrings are **the** spec the LLM
sees — written for the model.

| File | Tool | Reads | What for |
|---|---|---|---|
| `models.py` | (Pydantic) | — | `ShipmentRecord` / `LaneHistory` / `PortEvents` / their `*NotFound` siblings; validate tool I/O at the boundary |
| `shipment_lookup.py` | `lookup_shipment(shipment_id)` | `data/shipments/{id}.json` | Full shipment record — tracking events, carrier notes, downstream constraints |
| `carrier_history.py` | `carrier_history(lane)` | `data/lane_history.json` | 90-day per-carrier stats on a `{ORIGIN}-{DEST}` lane |
| `external_events.py` | `external_events(port_code)` | `data/external_events.json` | Weather / labor / congestion at a port |
| `search_sops.py` | `search_sops(query, k=4)` | ChromaDB `freight_sops` | Top-k SOP chunks with `{source, chunk_index, section, distance, text}` |
| `recall.py` | `recall_customer_history(name)`, `recall_shipment_history(id)` | `data/memory.sqlite3` | Past notes + corrections for the entity |

Two empty `__init__.py` files: `tools/__init__.py` (package marker, no
re-exports — agent imports each tool directly).

---

### `src/freight_copilot/retrieval/`

| File | Purpose |
|---|---|
| `__init__.py` | Re-exports `search`, `get_collection`, `reset_collection` |
| `store.py` | ChromaDB persistent client + `SentenceTransformerEmbeddingFunction` + `get_collection()` / `reset_collection()` / `search(query, k)` |
| `ingest.py` | Walks `data/sops/*.md`, splits with `RecursiveCharacterTextSplitter` (chunk_size=800, overlap=150), tags each chunk with `{source, chunk_index, section}`, populates the collection |

Run as a module: `PYTHONPATH=src python -m freight_copilot.retrieval.ingest`.
Idempotent — drops the collection and recreates.

---

### `src/freight_copilot/memory/`

| File | Purpose |
|---|---|
| `__init__.py` | Re-exports the public API of `store.py` |
| `store.py` | SQLite layer — schema + CRUD for `customer_notes`, `shipment_notes`, `corrections`. Honors `MEMORY_DB` env var for tests. |
| `seed.py` | Pre-populates the db with realistic historical notes for the 5 fixture customers/shipments. Run as `python -m freight_copilot.memory.seed`. Resets and re-inserts (idempotent). |
| `intent.py` | 7-class embedding-based intent classifier. Lazy-loaded singleton; mean-pooled centroids over hand-curated prototypes; cosine similarity. |

---

### `src/freight_copilot/prompts/`

| File | Purpose |
|---|---|
| `__init__.py` | Empty package marker |
| `system.py` | `BASE_SYSTEM_PROMPT` (constant — safety rails, tool list, citation rules, default response format) + `build_system_prompt(persona_name)` (composes BASE + persona addendum) |
| `personas.py` | Three `Persona` dataclasses (`ops_associate`/Tech, `finance_partner`/Finance, `customer_lead`/Customer); `get_persona()`, `list_personas()`, `DEFAULT_PERSONA` |

The base prompt and the persona addenda are both human-readable markdown.
The base prompt is where every safety rail lives. Persona addenda only
adjust **emphasis and structure**, never weaken the base.

---

### `src/freight_copilot/safety/`

| File | Purpose |
|---|---|
| `__init__.py` | Re-exports `scan_response`, `SafetyReport`, `SafetyFinding` |
| `patterns.py` | Compiled regexes: `commitment_language`, `unhedged_guarantee`, `hard_date_commitment`, `possible_pii`, `SOP_MENTION_REGEX` |
| `scanner.py` | `scan_response(text) → SafetyReport`. Two layers: pattern scan + SOP-citation cross-check vs `data/sops/*.md` |

Severity levels: `high` / `medium` / `low`. The scanner doesn't block — it
emits findings into the turn record and the UI renders them with badges.

---

## `app/` — Streamlit Phase 8

| File | Purpose |
|---|---|
| `streamlit_app.py` | Triage Console — chat-style UI, persona selector, 6 quick-prompt buttons (5 ATs + 1 adversarial), live event streaming, tool-trace and safety-findings expanders |
| `pages/1_📊_Monitoring.py` | KPI strip; active alerts (last 24h); intent / persona / tool distributions; safety findings (by severity + by pattern); latency timeline; raw turns table |
| `pages/2_🔍_Sessions.py` | Session picker (most recent first, with safety / error badges); per-session summary; turn-by-turn replay; raw JSONL dump |
| `_helpers.py` | `sys.path` injection so `freight_copilot` is importable; `fmt_ts(ts)` → "YYYY-MM-DD HH:MM:SS UTC", `fmt_ms(ms)` → "1.23s" / "850ms", `fmt_usd(v)` → "$0.0042" / "$3.50" |

Pages do their own `sys.path.insert(...)` at the top — Streamlit doesn't
share the entry script's path with sub-pages.

Run: `PYTHONPATH=src streamlit run app/streamlit_app.py` → `http://localhost:8501`.

---

## `data/`

```
data/
├── shipments/                 5 JSON fixtures, one per AT-1..AT-5
│   ├── FRT-1042.json          AT-1: customs hold, missing CI (Brookline Apparel)
│   ├── FRT-1043.json          AT-2: weather port closure (Lonestar Manufacturing)
│   ├── FRT-1044.json          AT-3: capacity rollover (Hanseatic Coffee)
│   ├── FRT-1045.json          AT-4: silent ETA slippage (Melbourne Tech)
│   └── FRT-1046.json          AT-5: HBL/MBL doc discrepancy (ACME Inc.)
├── sops/                      9 markdown SOPs (the RAG corpus)
│   ├── sop-customs-hold-missing-ci.md
│   ├── sop-weather-port-closure.md
│   ├── sop-capacity-rollover.md
│   ├── sop-silent-eta-slippage.md
│   ├── sop-doc-discrepancy-hbl-mbl.md
│   ├── sop-customer-tier-comms.md
│   ├── sop-demurrage-management.md
│   ├── sop-escalation-handoff.md
│   └── sop-customer-comm-style-guide.md
├── lane_history.json          Per-lane 90-day carrier performance (e.g. INNSA-USNYC, VNSGN-DEHAM)
├── external_events.json       Per-port events (weather/labor/congestion) keyed by UN/LOCODE
└── memory.sqlite3             Long-term memory db (gitignored, regenerate via seed.py)
```

Each shipment JSON has: `shipment_id`, `mode` (FCL/LCL/AIR), `service`,
`incoterm`, `container_count`, `container_type`, `origin`/`destination`
(port_code + name + country), `carrier`/`vessel`/`voyage`, `mbl_number` /
`hbl_number`, `etd` / `eta`, `shipper`/`consignee`/`customer`, `current_status`,
`exception_summary`, `documents`, `tracking_events[]`, `carrier_notes[]`,
`downstream_constraints` (SLA breach, vessel cutoff, demurrage rate).

The five fixtures are crafted so every acceptance test (AT-1..AT-5) and
adversarial probe (ADV-1..ADV-6) has the data it needs. Don't change them
without re-running the eval suite.

---

## `eval/`

Five runnable scripts + two YAML check specs.

| File | Phase | Purpose |
|---|---|---|
| `acceptance_tests.yaml` | 5 | AT-1..AT-5 prompts + check spec |
| `adversarial_probes.yaml` | 5 | ADV-1..ADV-6 prompts + refusal-check spec |
| `run_acceptance_tests.py` | 5 | Runs both YAML specs; deterministic predicate-based scoring; writes `docs/phase5-acceptance-results.{md,json}` |
| `compare_with_without_rag.py` | 4 | Runs AT-1..AT-5 twice each (RAG on/off); writes `docs/phase4-comparison.{md,json}` |
| `run_at3_multiturn.py` | 3 | 4-turn dialogue on AT-3 (rollover) including an adversarial probe; captures the trace |
| `run_cross_session_demo.py` | 6 | Two AgentSessions back-to-back; shows correction in A → recall in B |
| `run_persona_compare.py` | 7 | Same prompt across all three personas; writes `docs/phase7-persona-compare.{md,json}` |
| `capture_screenshots.py` | 8 | Playwright capture of the 3 Streamlit pages → `demo_screenshots/` |

All scripts inject `src/` into `sys.path` so they can be run directly
(`python eval/run_acceptance_tests.py`) without `PYTHONPATH=src`.

---

## `tests/`

12 test files, 85 tests, all LLM-free. Run: `pytest -q`.

| File | Tests for |
|---|---|
| `test_shipment_lookup.py` | `lookup_shipment` tool — happy path, all 5 fixtures, full payload shape, unknown ID |
| `test_carrier_history.py` | `carrier_history` — happy path, unknown lane returns error with available lanes |
| `test_external_events.py` | `external_events` — ports with events, ports without, unknown ports |
| `test_session_logger.py` | JSONL round-trip, append semantics, multiple sessions don't cross-contaminate |
| `test_retrieval.py` | RAG ingest writes 73 chunks; canonical queries hit expected SOPs |
| `test_safety_scanner.py` | 11 tests — patterns + cross-check; includes the `\b`-anchor regression for "we will execute" |
| `test_tool_validation.py` | Pydantic boundary validation; malformed fixtures raise `ValidationError` |
| `test_memory_store.py` | SQLite CRUD via tempfile db (uses `MEMORY_DB` env var) |
| `test_intent_classifier.py` | 7 intent classes + invariants (top-class margin, normalization) |
| `test_recall_tools.py` | Recall tools against the seeded production db |
| `test_personas.py` | 15 tests — registry, prompt composition, agent integration, safety rails constant across personas |
| `test_monitoring.py` | 12 tests — aggregation correctness, alert thresholds, percentile correctness |

`tests/__init__.py` exists but is empty (package marker).

---

## `docs/`

Two flavors of doc:

### Build-history docs (one per phase)

| File | Purpose |
|---|---|
| `01-problem-framing.md` | The Phase 1 contract — user persona, 5 ATs, success metrics, risk register, scope |
| `02-phase2-basic-agent.md` | Phase 2 — basic working agent (1 tool, CLI, system prompt safety rails) |
| `03-phase3-tools-and-memory.md` | Phase 3 — 3 tools, multi-turn `MemorySaver`, JSONL logging |
| `04-phase4-rag.md` | Phase 4 — ChromaDB + SOPs + ablation |
| `05-phase5-safety-and-eval.md` | Phase 5 — Pydantic + safety scanner + acceptance harness (11/11 pass) |
| `06-phase6-long-term-memory.md` | Phase 6 — SQLite + intent classifier + cross-session demo |
| `07-phase7-adaptive-personas.md` | Phase 7 — three personas + persona-compare demo |
| `08-phase8-deploy-and-monitor.md` | Phase 8 — Streamlit app + monitoring + alerts |

### Generated artifacts (committed for grading)

| File | Source |
|---|---|
| `phase2-at1-sample-run.txt` | Captured CLI session for AT-1 |
| `phase3-at3-multiturn-trace.txt` | Captured trace from `eval/run_at3_multiturn.py` |
| `phase4-comparison.md` / `.json` | Output of `eval/compare_with_without_rag.py` |
| `phase5-acceptance-results.md` / `.json` | Output of `eval/run_acceptance_tests.py` |
| `phase6-cross-session-trace.txt` | Captured trace from `eval/run_cross_session_demo.py` |
| `phase7-persona-compare.md` / `.json` | Output of `eval/run_persona_compare.py` |

### New top-level docs (this commit)

| File | Purpose |
|---|---|
| `project-overview.md` | Non-technical onramp — context, problem, AT cases, success metrics, phase journey |
| `architecture.md` | Technical architecture — agent loop, tools, RAG, memory, safety, monitoring, eval |
| `tech-stack.md` | Library / model / service inventory + rationale |
| `repo-guide.md` | This file — every directory and file explained |
| `communication.md` | How this codebase was built collaboratively (human ↔ AI workflow), conventions, and onboarding |

---

## `logs/` (gitignored)

One JSONL file per `AgentSession`: `logs/session-<thread_id>.jsonl`. One JSON
line per turn. The Streamlit Monitoring + Sessions pages and
`monitoring.read_turns()` are the consumers.

`logs/.gitkeep` keeps the directory present in fresh checkouts.

---

## `chroma_db/` (gitignored)

ChromaDB persistent index. Created by `python -m freight_copilot.retrieval.ingest`.
Safe to delete and regenerate at any time.

---

## `demo_screenshots/`

Three captured PNGs for the IITM submission packet:

```
01-triage-console.png    93 KB
02-monitoring.png       126 KB
03-sessions.png         344 KB
```

Captured by `eval/capture_screenshots.py` (Playwright with Chromium, waits
for Streamlit's WebSocket render). `.gitkeep` keeps the directory present.

---

## `.claude/`

Editor state, gitignored except where intentionally committed. Currently
contains:
- `launch.json` — Streamlit dev-server preview config.
- `settings.local.json` — local editor settings.

Not part of the runtime; safe to ignore.

---

## Top-level config files

### `.gitignore`
Standard Python ignores + `.venv/`, `.env`, `chroma_db/`, `data/memory.sqlite3`,
`logs/*.jsonl`, `__pycache__/`. Keeps committed: source, fixtures, SOPs,
phase docs, screenshots.

### `.env.example`
Template — copy to `.env` and fill in. Documents all env vars (see
[tech-stack.md §14](tech-stack.md#14-environment-variables)).

### `pyproject.toml`
Project metadata + ruff config.

### `requirements.txt`
Pinned dependencies, grouped by purpose (see
[tech-stack.md §15](tech-stack.md#15-dependency-tree-summary)). Comment block
above NumPy explains the `<2.0` pin (torch 2.2.2 macOS x86_64 ABI).

### `README.md`
Quickstart + status table. Short by design — the "deep" docs are in `docs/`.

### `LICENSE`
MIT.

### `Capstone-Project-...pdf`
The IITM assignment brief. Reference only — the project is the implementation.

---

## How to find your way around in 60 seconds

If you want to understand…

- **What this project is** → [`project-overview.md`](project-overview.md)
- **What a single agent turn does step-by-step** → [`architecture.md` §2](architecture.md#2-the-agent-loop--what-happens-when-a-user-types-a-message)
- **What tools the agent has** → [`architecture.md` §3](architecture.md#3-the-6-tools)
- **What's in the system prompt** → [`src/freight_copilot/prompts/system.py`](../src/freight_copilot/prompts/system.py)
- **How RAG works** → [`architecture.md` §5](architecture.md#5-rag-pipeline) and [`src/freight_copilot/retrieval/`](../src/freight_copilot/retrieval/)
- **How memory works** → [`architecture.md` §6](architecture.md#6-memory-subsystem) and [`src/freight_copilot/memory/`](../src/freight_copilot/memory/)
- **How safety is enforced** → [`architecture.md` §7](architecture.md#7-safety-subsystem) and [`src/freight_copilot/safety/`](../src/freight_copilot/safety/)
- **What the Streamlit pages look like** → [`demo_screenshots/`](../demo_screenshots/) and [`docs/08-phase8-deploy-and-monitor.md`](08-phase8-deploy-and-monitor.md)
- **How acceptance is evaluated** → [`eval/acceptance_tests.yaml`](../eval/acceptance_tests.yaml) + [`eval/run_acceptance_tests.py`](../eval/run_acceptance_tests.py)
