# Tech Stack

What every library, model, and service in this project is for.

---

## 1. Headline choices

| Layer | Choice | Why |
|---|---|---|
| LLM | Anthropic **Claude Haiku 4.5** (dev), Sonnet 4.6 (eval/demo) | Strong tool use; Haiku is cheap enough that the $20 budget is comfortable; Sonnet kept for high-fidelity final runs |
| Agent runtime | **LangChain + LangGraph** (Track A of the rubric) | Canonical ReAct via `create_react_agent`; well-documented checkpointer for multi-turn; the same primitive scales across all 9 phases |
| Vector store | **ChromaDB** (persistent client, on-disk) | Free, local, no service to run, 73 chunks fits comfortably |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 384-dim, runs on CPU, $0; reused for both RAG and intent classification |
| Long-term memory | **SQLite** (stdlib) | Zero ops; one file; easy audit trail |
| UI | **Streamlit** | Multi-page chat UI in <500 LOC; native components for KPIs, charts, replays |
| Tracing | **LangSmith** (optional) | Set `LANGCHAIN_TRACING_V2=true` + key in `.env` |
| Tests | **pytest** | 85 tests across 12 files, all LLM-free |
| Lint / format | **ruff** | One tool for both; config in `pyproject.toml` |

---

## 2. The LLM — Anthropic Claude

**Provider:** Anthropic API (direct, via `anthropic` SDK behind `langchain-anthropic`).

**Models:**

| Model ID | Where used | Why |
|---|---|---|
| `claude-haiku-4-5-20251001` | Default for dev iteration, all phases | $1/MTok in, $5/MTok out — cheap enough that the project ran end-to-end inside ~$0.81 |
| `claude-sonnet-4-6` | Reserved for final eval runs and demo recording | Higher fidelity on long, structured drafts |

**Configuration:** `temperature=0`, `max_tokens=2048`. Set in
[`src/freight_copilot/agent.py`](../src/freight_copilot/agent.py) via
`ChatAnthropic(model=..., temperature=0, max_tokens=2048)`.

**Override:** `ANTHROPIC_MODEL` env var swaps the default at runtime. Defined
in [`.env.example`](../.env.example).

**Why Anthropic specifically:** Strong tool-use behavior, transparent
guidance for "don't commit actions" framing, and the cohort's IITM Capstone
gives every student starting credit on this provider.

---

## 3. Agent framework — LangChain + LangGraph

**Track A** of the IITM rubric. The choice here is the spine of every phase.

### LangChain

- `from langchain_core.tools import tool` — the `@tool` decorator turns a
  Python function into an LLM-visible tool. The function's docstring **is**
  the spec the model sees, so each docstring is written like an
  instruction-card for the model (when to call, what to expect, how to cite).
- `from langchain_anthropic import ChatAnthropic` — the chat model wrapper.
- `from langchain_text_splitters import RecursiveCharacterTextSplitter` —
  used in [`retrieval/ingest.py`](../src/freight_copilot/retrieval/ingest.py)
  for chunking SOPs (chunk_size=800, overlap=150, markdown-aware separators).

### LangGraph

- `from langgraph.prebuilt import create_react_agent` — the canonical ReAct
  agent runtime. The agent is built once per `AgentSession` with the model,
  the tools list, the composed system prompt, and a checkpointer.
- `from langgraph.checkpoint.memory import MemorySaver` — in-process
  per-`thread_id` checkpointer. Multi-turn message history "for free" once
  you pass `config={"configurable": {"thread_id": tid}}`.

### Why LangGraph over a hand-rolled loop

Less code, well-tested ReAct routing, and we extend the same primitive in
later phases (more tools, persona-aware prompts, custom event streaming) —
no rewrite needed at any phase boundary. See [`docs/02-phase2-basic-agent.md`](02-phase2-basic-agent.md)
for the original decision log.

---

## 4. Retrieval / RAG

| Component | Library | Purpose |
|---|---|---|
| Vector DB | `chromadb` (PersistentClient on `./chroma_db/`) | Stores 73 SOP chunks with metadata `{source, chunk_index, section}`, cosine distance |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` via Chroma's `SentenceTransformerEmbeddingFunction` | 384-dim sentence embeddings, runs locally on CPU, $0 inference |
| Chunker | `langchain_text_splitters.RecursiveCharacterTextSplitter` | Markdown-aware splits (`\n## `, `\n### `, …) — keeps section boundaries intact |
| Tool wrapper | `freight_copilot.tools.search_sops` | LangChain `@tool` over `retrieval.store.search()`; returns top-k JSON |

**Why local embeddings:** The same model is reused for the intent classifier
(see §5) — already loaded in process, near-zero marginal cost. No external
embedding API needed.

**Why ChromaDB:** Local-first, persistent, no service. The collection is
called `freight_sops` and has metadata `{"hnsw:space": "cosine"}`. Re-ingest
is idempotent: drop the collection, recreate, repopulate.

---

## 5. Long-term memory — SQLite

`data/memory.sqlite3`, three tables — `customer_notes`, `shipment_notes`,
`corrections`. See [architecture.md §6](architecture.md#6-memory-subsystem)
for schema and writes.

**Why SQLite:** Stdlib (no install), one file (easy to inspect, easy to
backup, easy to gitignore), CRUD is trivial, indexes give us O(log n) recall
even with thousands of notes. Pydantic / dataclass models on top
([`store.py`](../src/freight_copilot/memory/store.py)) keep the API
type-clean.

---

## 6. Intent classification

**Implementation:** [`src/freight_copilot/memory/intent.py`](../src/freight_copilot/memory/intent.py).

- 7 intents: `triage_request`, `follow_up`, `policy_question`,
  `draft_request`, `correction`, `commit_request`, `meta`.
- 6 hand-curated prototype phrases per intent → mean-pooled centroid per intent.
- Classification: cosine similarity to nearest centroid.
- Embedding model: same `all-MiniLM-L6-v2` already loaded for RAG.

**Why embedding-based instead of LLM-based:**
- Free — reuses the loaded model.
- Fast — ~10ms per classification, runs locally.
- Stable — no LLM nondeterminism.
- Sufficient for a 7-class problem with clear prototypes.

---

## 7. UI — Streamlit

Three pages (one entry script, two auto-discovered pages under `app/pages/`):

| Page | File |
|---|---|
| Triage Console | [`app/streamlit_app.py`](../app/streamlit_app.py) |
| 📊 Monitoring | [`app/pages/1_📊_Monitoring.py`](../app/pages/1_📊_Monitoring.py) |
| 🔍 Sessions | [`app/pages/2_🔍_Sessions.py`](../app/pages/2_🔍_Sessions.py) |

**Used Streamlit primitives:** `st.chat_message`, `st.chat_input`,
`st.status`, `st.expander`, `st.metric`, `st.bar_chart`, `st.line_chart`,
`st.dataframe`, `st.session_state`, `st.toast`, `st.rerun`,
`st.selectbox`, `st.set_page_config`. No third-party Streamlit plugins.

**Why Streamlit (not Gradio / FastAPI):** The rubric calls out
"Streamlit/Gradio/Vercel"; Streamlit's chat UI primitives + native multi-page
support meant the entire app fits in <500 LOC across 3 files.

---

## 8. Data validation — Pydantic v2

[`src/freight_copilot/tools/models.py`](../src/freight_copilot/tools/models.py)

Every tool boundary validates its return value against a Pydantic model
*before* returning to the LLM:

| Model | Tool |
|---|---|
| `ShipmentRecord` / `ShipmentNotFound` | `lookup_shipment` |
| `LaneHistory` / `LaneNotFound` | `carrier_history` |
| `PortEvents` / `PortNotCovered` | `external_events` |

Models are `extra="allow"` so fixtures can carry forward-compat fields
without breaking — but every field the agent depends on is required. A
malformed fixture raises `ValidationError` at the boundary instead of
silently producing wrong agent behavior.

Pydantic's `model_dump_json(exclude_none=False)` is what the tool actually
returns to the LLM (string-encoded JSON).

---

## 9. Observability and tracing

### Per-turn JSONL logs

[`src/freight_copilot/session_logger.py`](../src/freight_copilot/session_logger.py)
writes one JSON line per turn to `logs/session-<thread_id>.jsonl`. Schema:
`TurnRecord` dataclass — see [architecture.md §2](architecture.md#step-6--persist--log)
for the full schema.

These logs are the **single source of truth** the monitoring dashboard reads
from. No parallel logging system.

### LangSmith (optional)

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY=lsv2_...` in `.env` to
get distributed tracing of every LangGraph run on
[smith.langchain.com](https://smith.langchain.com). Useful for debugging
unexpected tool-routing decisions.

### Monitoring dashboard

[`src/freight_copilot/monitoring.py`](../src/freight_copilot/monitoring.py)
is a pure-Python data layer. Three primary functions:

```python
read_turns()              # all turns across all session files
aggregate_metrics(turns)  # counts, latency p50/p95, tokens, $cost
derive_alerts(turns, AlertThresholds(...))
```

Cost is computed at public Anthropic Haiku 4.5 prices ($1/MTok input, $5/MTok output).

---

## 10. Testing

**Framework:** pytest. **Test count:** 85 across 12 files. **Cost:** $0 — no
LLM calls in tests.

| File | Covers |
|---|---|
| `test_shipment_lookup.py` | Tool: happy path, all 5 fixtures, full-payload shape, unknown ID |
| `test_carrier_history.py` | Tool: happy path, unknown lane error |
| `test_external_events.py` | Tool: ports with/without events, unknown ports |
| `test_session_logger.py` | JSONL round-trip, append semantics, multiple sessions |
| `test_retrieval.py` | RAG: ingest writes 73 chunks; canonical queries hit expected SOPs |
| `test_safety_scanner.py` | 11 tests including the `\b`-anchor regression for "we will execute" |
| `test_tool_validation.py` | Pydantic boundary validation — malformed fixtures raise loudly |
| `test_memory_store.py` | SQLite CRUD via tempfile db (no clobbering production) |
| `test_intent_classifier.py` | 7-intent routing parametrized + invariants |
| `test_recall_tools.py` | Recall tools against seeded production db |
| `test_personas.py` | Registry, prompt composition, agent integration, safety rails constant |
| `test_monitoring.py` | Aggregation correctness, alert thresholds, percentile correctness |

`pytest-asyncio` is in requirements but only needed if you add async tools.

---

## 11. Evaluation libraries

| Library | Why |
|---|---|
| `pyyaml` | Acceptance test specs are YAML for readability |
| `ragas` (planned, Phase 9) | Faithfulness, answer relevance, context precision metrics |
| `datasets` (planned, Phase 9) | RAGAs needs HuggingFace `Dataset` objects |
| `playwright` (Phase 8) | Capture Streamlit screenshots — `chrome --headless --screenshot` doesn't work because Streamlit content streams in via WebSocket after page load |

---

## 12. Lint / format / dev

| Tool | Config | Used for |
|---|---|---|
| `ruff` | [`pyproject.toml`](../pyproject.toml) | Linting + formatting (one tool, replaces black + isort + flake8) |
| `python-dotenv` | — | Loads `.env` for `ANTHROPIC_API_KEY` etc. `load_dotenv(override=True)` so the project's `.env` wins over stale empty-valued env vars from the parent shell |
| `loguru` | — | In requirements but not heavily used today |
| `tenacity` | — | In requirements; available for retry logic |
| `httpx` | — | Available for any direct HTTP calls (not currently used) |

---

## 13. Python and platform

- **Python 3.12** required. Not 3.14 — torch 2.2.2 (the last x86_64 macOS
  build) was compiled against NumPy 1.x, which doesn't ship a 3.14 wheel.
  This is documented in `requirements.txt` as a comment.
- **Platform tested:** macOS Darwin 24.5.0 (Apple Silicon developer machine
  via x86_64 Rosetta for torch). Streamlit + ChromaDB run anywhere.
- **NumPy pinned to <2.0** for the same torch ABI reason.

---

## 14. Environment variables

From [`.env.example`](../.env.example):

| Var | Required? | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ required | Auth for the Claude API |
| `ANTHROPIC_MODEL` | optional | Override the default `claude-haiku-4-5-20251001` (e.g. for Sonnet on demo runs) |
| `LANGCHAIN_TRACING_V2` | optional | Set to `true` to emit LangSmith traces |
| `LANGCHAIN_API_KEY` | optional | LangSmith API key (only if tracing is on) |
| `LANGCHAIN_PROJECT` | optional | LangSmith project name (default: `freight-ops-copilot`) |
| `LOG_LEVEL` | optional | Default `INFO` |
| `CHROMA_PERSIST_DIR` | optional | Override the chroma_db location (default `./chroma_db`) |
| `EMBEDDING_MODEL` | optional | Override embedding model (default `sentence-transformers/all-MiniLM-L6-v2`) |
| `MEMORY_DB` | optional (test-only) | Override SQLite path; used by tests to point at a tempfile so they don't clobber `data/memory.sqlite3` |

---

## 15. Dependency tree summary

The `requirements.txt` groups:

```
# --- Core LLM + Agent framework ---
langchain, langchain-anthropic, langchain-community, langgraph, langsmith

# --- Retrieval / RAG ---
chromadb, sentence-transformers

# --- LLM SDK (used by langchain-anthropic) ---
anthropic

# --- App / UI ---
streamlit

# --- Data + utilities ---
numpy<2.0 (torch ABI), pydantic v2, python-dotenv, pyyaml, httpx, loguru, tenacity

# --- Evaluation ---
ragas, datasets

# --- Dev / Test ---
pytest, pytest-asyncio, ruff, playwright (Phase 8 screenshots)
```

Total install footprint is dominated by `torch` (transitive dep of
`sentence-transformers`) and `chromadb` (with its bundled HNSW index). On a
fresh venv expect ~3–4 GB of disk for site-packages.

---

## 16. What we deliberately did NOT use

| Choice avoided | Reason |
|---|---|
| OpenAI / mixed-provider | The capstone scenario is built around Anthropic; mixing providers would weaken the prompt-caching/cost story without buying anything |
| Pinecone / Weaviate / managed vector DB | ChromaDB local is enough at 73 chunks; no service to run |
| Postgres for memory | SQLite is enough at the data volumes here |
| FastAPI / Flask | Streamlit covers the UI; no separate API layer is needed |
| Gradio | Streamlit's multi-page support and chat primitives fit better |
| LangChain Memory primitives | LangGraph's `MemorySaver` covers short-term; SQLite is simpler than `ConversationSummaryMemory` etc. for long-term |
| LLM-as-judge in CI | Non-deterministic — we use rule-based predicates for CI signal stability and layer LLM-judge on top in Phase 9 |
| OpenAI embeddings | Local sentence-transformers is free and good enough; one less external dep |
