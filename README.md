# Freight Operations Triage Copilot

> **IITM Applied AI Capstone — Scenario 1: Business Operations Copilot (Decision Support)**
>
> An AI agent that helps freight-forwarding operations associates triage shipment exceptions — diagnose root cause, surface relevant SOPs, recommend next actions, and draft customer communications. **Decision support only**: the agent never commits actions.

📦 **Submission deliverables:**
- 📋 [Problem Framing](docs/01-problem-framing.md) — the contract for everything that followed
- 📊 [**Evaluation Report**](docs/EVALUATION_REPORT.md) — 4-method eval; honest about what works and what doesn't
- 🪞 [**Reflection Report**](docs/REFLECTION_REPORT.md) — what went well, what didn't, what I'd do next
- 🖼 Demo screenshots in [`demo_screenshots/`](demo_screenshots/) (Streamlit app, captured via Playwright)
- 🔁 Every number in the reports is reproducible — see [§Reproducing the evaluation](#reproducing-the-evaluation)

---

## Project status — all 9 phases ✅

| Phase | Description | Status | Doc |
|---|---|---|---|
| 1 | Problem framing & success metrics | ✅ done | [01-problem-framing.md](docs/01-problem-framing.md) |
| 2 | Basic working agent (LLM + tool) | ✅ done | [02-phase2-basic-agent.md](docs/02-phase2-basic-agent.md) |
| 3 | Tools + multi-turn memory | ✅ done | [03-phase3-tools-and-memory.md](docs/03-phase3-tools-and-memory.md) |
| 4 | Knowledge & retrieval (RAG) | ✅ done | [04-phase4-rag.md](docs/04-phase4-rag.md) |
| 5 | Real test data + safeguards | ✅ done | [05-phase5-safety-and-eval.md](docs/05-phase5-safety-and-eval.md) |
| 6 | Long-term memory & intent recognition | ✅ done | [06-phase6-long-term-memory.md](docs/06-phase6-long-term-memory.md) |
| 7 | Adaptive behavior (role + tone) | ✅ done | [07-phase7-adaptive-personas.md](docs/07-phase7-adaptive-personas.md) |
| 8 | Deploy + monitor (Streamlit) | ✅ done | [08-phase8-deploy-and-monitor.md](docs/08-phase8-deploy-and-monitor.md) |
| 9 | Evaluation framework + reports | ✅ done | [09-phase9-evaluation-and-reports.md](docs/09-phase9-evaluation-and-reports.md) |

**Tests:** 85 passing  ·  **Total cost:** ~$1.30 / $20 Anthropic budget (6.5%)  ·  **PRs:** 7 merged

---

## What this agent does

Given a shipment ID where ops has flagged an exception, it:

1. **Diagnoses** the root cause from the shipment record + tracking events + carrier notes
2. **Recalls** prior triages and customer-specific quirks from long-term memory
3. **Searches the SOP corpus** (RAG over 9 markdown playbooks → 73 chunks in ChromaDB)
4. **Recommends ranked next actions** with expected resolution times
5. **Drafts a customer comm** in tone calibrated to the customer's tier
6. **Flags downstream exposure** — SLA breach, vessel cutoff, demurrage

…and **never** commits any of those actions. It hands them back to the human ops associate.

### What makes it interesting (vs. a chat-with-data demo)

- **Multi-source grounding** — every claim is traceable to one of: shipment record, lane history, port event, retrieved SOP chunk, or recalled correction.
- **Output safety scanner** — regex + SOP-citation cross-check that catches hallucinated filenames, commitment language, unhedged dates, and PII patterns at the boundary.
- **Three personas** (Tech / Finance / Customer) compose on top of the same base prompt and the same safety rails, switchable mid-session.
- **Long-term memory across sessions** — corrections persist to SQLite and are auto-recalled on subsequent visits.
- **Live monitoring dashboard** — KPIs, alerts, distributions, latency timeline, all read from the JSONL session logs the agent has been writing since Phase 3.

---

## Stack

| Layer | Choice |
|---|---|
| LLM | Anthropic Claude — Haiku 4.5 (agent), Sonnet 4.6 (eval judge) |
| Agent framework | LangChain + LangGraph |
| RAG | ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` (local, free) |
| Long-term memory | SQLite (`data/memory.sqlite3`) |
| UI | Streamlit (multi-page) |
| Tracing / eval | RAGAs + LLM-as-judge (Sonnet 4.6) |
| Tests | pytest |
| Lint / format | ruff |
| Screenshots | Playwright |

---

## Repo layout

```
.
├── app/                       # Phase 8 Streamlit app
│   ├── streamlit_app.py       #   Triage Console (main page)
│   └── pages/                 #   Monitoring + Sessions pages
├── data/
│   ├── shipments/             # 5 fixture shipments (one per AT case)
│   ├── sops/                  # 9 SOPs (RAG corpus)
│   ├── lane_history.json      # 90-day carrier perf per lane
│   └── external_events.json   # weather/labor/congestion per port
├── demo_screenshots/          # Submission deliverable
├── docs/
│   ├── 01-problem-framing.md  # Phase 1 deliverable
│   ├── 02..09-phaseN-*.md     # Per-phase build docs
│   ├── EVALUATION_REPORT.md   # ⭐ submission deliverable
│   ├── REFLECTION_REPORT.md   # ⭐ submission deliverable
│   └── phase9-*-results.*     # Raw eval data
├── eval/                      # Eval harnesses (Phase 4-9)
├── src/freight_copilot/
│   ├── agent.py               # AgentSession + build_agent
│   ├── memory/                # SQLite store + intent classifier
│   ├── prompts/               # System prompt + 3 personas
│   ├── retrieval/             # Chroma + ingest
│   ├── safety/                # Output scanner + patterns
│   ├── session_logger.py      # JSONL turn records
│   ├── monitoring.py          # Aggregations for the dashboard
│   └── tools/                 # 6 LangChain tools
├── tests/                     # 85 tests
├── .env.example
├── requirements.txt
└── pyproject.toml
```

---

## Setup

```bash
# 1. Python 3.12 venv (3.12 specifically — see docs/02-phase2-basic-agent.md)
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure env
cp .env.example .env
# edit .env — fill in ANTHROPIC_API_KEY (and optionally LANGCHAIN_API_KEY)

# 4. Build the SOP index (Chroma) — one-time
PYTHONPATH=src python -m freight_copilot.retrieval.ingest

# 5. Seed the long-term memory db — one-time, optional but recommended
PYTHONPATH=src python -m freight_copilot.memory.seed
```

---

## Run

```bash
# Streamlit web app — main UI: Triage Console + Monitoring + Sessions
PYTHONPATH=src streamlit run app/streamlit_app.py
# → http://localhost:8501

# CLI agent — same agent, terminal interface
PYTHONPATH=src python -m freight_copilot
```

In the CLI, try:
```
> Triage shipment FRT-1042
> /role finance_partner
> What's the cost exposure if the hold extends another week?
> /role customer_lead
> Draft me a Platinum-tier email I can send after I confirm with finance
```

---

## Reproducing the evaluation

Every number in the [Evaluation Report](docs/EVALUATION_REPORT.md) is reproducible from the repo:

```bash
# Multi-seed acceptance + adversarial probes (~10 min, ~$0.30)
PYTHONPATH=src python eval/run_multi_seed.py --seeds 3

# Independent LLM-as-judge (~1 min, ~$0.07 — uses Sonnet 4.6)
PYTHONPATH=src python eval/run_llm_judge.py

# RAGAs faithfulness / answer-relevancy / context-precision (~3 min, ~$0.20)
PYTHONPATH=src python eval/run_ragas.py

# Latency profile (no LLM calls — reads logs/)
PYTHONPATH=src python eval/profile_latency.py
```

Total wall-clock for a full re-evaluation: ~15 minutes. Total cost: ~$0.50.

---

## Tests + lint

```bash
PYTHONPATH=src pytest tests/             # 85 passing
ruff check .
ruff format .
```

---

## Author

**Ashish Zanwar** — `ashish.zanwar@freightify.com`
IITM Applied AI capstone, 2026.

## License

See [LICENSE](LICENSE).
