# Freight Operations Copilot

> **IITM Applied AI Capstone — Scenario 1: Business Operations Copilot (Decision Support)**
>
> An AI agent that helps freight-forwarding operations associates triage shipment exceptions — diagnose root cause, surface relevant SOPs, recommend next actions, and draft customer communications. **Decision support only**: the agent never commits actions.

---

## Project status

| Phase | Description | Status |
|---|---|---|
| 1 | Problem framing & success metrics | ✅ done |
| 2 | Basic working agent (LLM + tool) | ✅ done |
| 3 | Tools + multi-turn memory | ✅ done |
| 4 | Knowledge & retrieval (RAG) | ⏳ pending |
| 5 | Real test data + safeguards | ⏳ pending |
| 6 | Long-term memory & intent recognition | ⏳ pending |
| 7 | Adaptive behavior (role + tone) | ⏳ pending |
| 8 | Deploy + monitor (Streamlit) | ⏳ pending |
| 9 | Evaluation framework | ⏳ pending |

---

## Stack

| Layer | Choice |
|---|---|
| LLM | Anthropic Claude — Haiku 4.5 (dev), Sonnet 4.6 (eval/demo) |
| Agent framework | LangChain + LangGraph |
| RAG | ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` |
| UI | Streamlit |
| Tracing / eval | LangSmith + RAGAs |
| Tests | pytest |
| Lint / format | ruff |

---

## Repo layout

```
.
├── app/                       # Streamlit demo (Phase 8)
├── data/
│   ├── shipments/             # Mock shipment / tracking fixtures
│   └── sops/                  # Synthetic ops SOPs (RAG corpus)
├── demo_screenshots/          # Screenshots for submission
├── docs/                      # Problem framing, architecture, eval, reflection
├── eval/                      # Acceptance test cases + evaluation harness
├── src/freight_copilot/       # Agent code
│   ├── tools/                 # Function-calling tools
│   ├── memory/                # Short- and long-term memory
│   ├── retrieval/             # RAG pipeline
│   └── prompts/               # System prompts & templates
├── tests/                     # Unit / integration tests
├── .env.example               # Env var template
├── requirements.txt
└── pyproject.toml             # ruff config
```

---

## Setup

```bash
# 1. Create + activate venv (Python 3.12 required)
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install deps
pip install -r requirements.txt

# 3. Configure env
cp .env.example .env
# then edit .env — fill in ANTHROPIC_API_KEY (and LANGCHAIN_API_KEY if using LangSmith)

# 4. Smoke test
python -c "from freight_copilot import __version__; print(__version__)"
```

---

## Run

```bash
# CLI agent (Phase 2+)
python -m freight_copilot.agent

# Streamlit app (Phase 8)
streamlit run app/streamlit_app.py
```

---

## Tests + lint

```bash
pytest -q
ruff check .
ruff format .
```

---

## Author

**Ashish Zanwar** — IITM Applied AI capstone, 2026.

## License

See [LICENSE](LICENSE).
