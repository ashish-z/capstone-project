# Phase 8 — Deploy & Monitor (Streamlit)

**Goal:** Move from "the agent is great if you happen to be a developer with a terminal open" to **"the agent is a usable web app, with a live operational view of every session it's run."**

The rubric for this phase calls for: a deployed UI (Streamlit/Gradio), basic monitoring, alerts for failures, and reviewable error reports. Phase 8 ships all four as a single 3-page Streamlit app sitting on top of the JSONL logs we've been writing since Phase 3.

## What's new vs. Phase 7

| Capability | Phase 7 | Phase 8 |
|---|---|---|
| Interface | CLI (`python -m freight_copilot`) | **Streamlit web app** with chat UI |
| Persona switching | `/role` CLI command | Sidebar selectbox + persisted across reruns |
| Visibility into past sessions | Read JSONL by hand | **Sessions Inspector** page (browse + replay) |
| Operational metrics | None | **Monitoring** page (KPIs, distributions, latency timeline) |
| Alerts | None | Active-alerts panel: P95 latency, error rate, safety findings, cost burn |
| Reproducible screenshots | n/a | Playwright-based capture script |

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  app/  (Streamlit, multi-page)                                   │
│                                                                  │
│  streamlit_app.py         🚚 Triage Console                      │
│   ├─ persona selector + 6 quick prompts                          │
│   ├─ chat-style turn history with intent / tool / safety badges  │
│   └─ live status while the agent streams                         │
│                                                                  │
│  pages/                                                          │
│  ├─ 1_📊_Monitoring.py     Aggregate metrics + active alerts     │
│  └─ 2_🔍_Sessions.py       Browse any logged session             │
│                                                                  │
│  _helpers.py              path setup + tiny formatters           │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
              src/freight_copilot/monitoring.py
              ├─ read_turns()           parse logs/session-*.jsonl
              ├─ aggregate_metrics()    counts, percentiles, cost
              ├─ derive_alerts()        active alerts vs thresholds
              ├─ list_sessions()        per-session summary
              └─ read_session(tid)      one session, in turn order
                                   │
                                   ▼
                       logs/session-*.jsonl
                       (one file per AgentSession,
                        appended to on every turn since Phase 3)
```

The monitoring pages are **read-only over the same JSONL logs** the CLI has been writing since Phase 3. No new data store. No background process. Just refresh-on-load.

## Files added / changed

| File | Status | Purpose |
|---|---|---|
| [`app/streamlit_app.py`](../app/streamlit_app.py) | rewritten | Triage Console — chat UI with persona selector, quick prompts, live event streaming |
| [`app/pages/1_📊_Monitoring.py`](../app/pages/1_📊_Monitoring.py) | new | Active alerts + KPI strip + 4 distribution charts + latency timeline + raw-turns table |
| [`app/pages/2_🔍_Sessions.py`](../app/pages/2_🔍_Sessions.py) | new | Per-session summary + turn-by-turn replay with tool traces, safety findings, raw JSONL |
| [`app/_helpers.py`](../app/_helpers.py) | new | `sys.path` injection + format helpers (`fmt_ts`, `fmt_ms`, `fmt_usd`) |
| [`src/freight_copilot/monitoring.py`](../src/freight_copilot/monitoring.py) | new | Pure-Python data layer — reads JSONL, aggregates, derives alerts |
| [`eval/capture_screenshots.py`](../eval/capture_screenshots.py) | new | Playwright-based screenshot capture for the 3 pages |
| [`tests/test_monitoring.py`](../tests/test_monitoring.py) | new | 12 tests for aggregation, alert thresholds, percentile correctness |
| [`.claude/launch.json`](../.claude/launch.json) | new | Streamlit dev-server config for editor preview |

Tests: 73 → **85 passing**.

## Running it locally

```bash
# 1. Activate the venv
source .venv/bin/activate

# 2. Make sure .env has your ANTHROPIC_API_KEY (Phase 2 setup)

# 3. Re-seed the long-term memory db (one-time, optional)
PYTHONPATH=src python -m freight_copilot.memory.seed
PYTHONPATH=src python -m freight_copilot.retrieval.ingest

# 4. Start the Streamlit app
PYTHONPATH=src streamlit run app/streamlit_app.py

# Now open http://localhost:8501
#   - Triage Console (main page)
#   - Monitoring (sidebar)
#   - Sessions (sidebar)
```

The first triage call cold-starts the agent (chroma + sentence-transformers model load, ~3–5s). Subsequent calls are fast.

## Triage Console — what each piece does

| UI element | Maps to |
|---|---|
| **Persona selector** (sidebar) | `AgentSession.set_persona()` — preserves message history across the switch |
| **Quick prompts** (sidebar) | The 5 acceptance test prompts + 1 adversarial probe — one-click reproducibility |
| **🔄 Reset session** | Spawns a new `AgentSession` (new `thread_id`, fresh memory, same persona) |
| **Live status panel** | Streams `intent` → `tool_call` → `tool_result` → `safety` → `final` events as they fire |
| **Tool trace expander** | Per-turn: every tool call with its args + truncated result |
| **Safety findings expander** | Auto-shown if any high-severity finding fires |

## Monitoring — KPIs, distributions, alerts

Reads every `logs/session-*.jsonl` on disk on every page load.

### KPI strip

- **Sessions** / **Turns** / **Errors**
- **P95 latency** / **Median latency** (against the Phase 1 target of P95 < 8s)
- **Cost** at Haiku 4.5 prices ($1/MTok in, $5/MTok out)

### Active alerts (last 24h)

Configurable via [`AlertThresholds`](../src/freight_copilot/monitoring.py):

| Alert | Severity | Default threshold |
|---|---|---|
| High-severity safety finding (per occurrence) | high | any |
| P95 latency over threshold | medium | 8,000 ms |
| Error rate over threshold | high | 5 % |
| Cost burn rate | medium | $1.00 / hour |

Alerts surface inline on the Monitoring page. We saw the **P95 latency** alert fire automatically on the demo data — current P95 is **38.5 s**, well above the 8 s target. (See "Real findings" below.)

### Distributions

- Intent distribution (`triage_request`, `follow_up`, etc. — Phase 6)
- Persona usage (`ops_associate` / `finance_partner` / `customer_lead` — Phase 7)
- Tool call frequency (which tools the agent reaches for most)
- Safety findings by severity AND by pattern

### Latency timeline + raw turns table

A line chart of every turn's wall-clock latency, and a tabular dump of the raw turn records for deep-dive inspection.

## Sessions Inspector — replay any logged session

Browse every session that's ever run (most recent first), pick one, and see:

- Per-session summary: turns, persona, model, first/last UTC timestamps
- Per-turn: intent, persona, latency, tokens, user input, tool trace, safety findings, final response
- Safety / error badges in the session list (🔴 / ⚠) for triage at a glance
- Collapsible **raw JSONL** dump for off-Streamlit inspection

This is the "review error reports" deliverable from the rubric — and it works for successful runs too, which is the more common debugging case.

## Real findings the monitoring surfaced

Even on Phase 8's first end-to-end run, the dashboard surfaced two operational findings worth recording:

### 1. P95 latency is 5× the Phase 1 target

Across the 4 turns logged so far, **P95 = 38.5s** vs. our Phase 1 target of **<8s**. Every turn is a heavy multi-tool flow (lookup → recall_shipment → recall_customer → search_sops → final), and each tool call adds round-trip latency.

This is a real regression from the Phase 3 numbers (P95 ~22s on a smaller toolset). Phase 9 will profile token-by-token to decide between:
- Prompt caching to amortize the system prompt across turns
- Parallel tool calling (LangGraph supports it; we currently sequence)
- Switching to Sonnet 4.6 only for the final response generation

### 2. Persona usage is well-balanced

The four logged turns split as ops_associate (2), finance_partner (1), customer_lead (1) — the persona switching mechanism from Phase 7 is being exercised. The `set_persona()` design (rebuild agent, keep checkpointer) is letting us flip personas mid-session without losing history.

## Reproducible screenshots

`eval/capture_screenshots.py` uses Playwright with a real Chromium so it waits for Streamlit's WebSocket-streamed UI to settle (plain `chrome --headless --screenshot` captures a blank loading screen).

```bash
# In one terminal:
PYTHONPATH=src streamlit run app/streamlit_app.py

# In another:
PYTHONPATH=src python eval/capture_screenshots.py
# → demo_screenshots/01-triage-console.png
# → demo_screenshots/02-monitoring.png
# → demo_screenshots/03-sessions.png
```

Output sizes ~92–344 KB each (full 1280×2200 page captures). Used for the IITM submission packet.

## Cost actuals (this phase)

| Item | Cost |
|---|---|
| Tests (no LLM, including 12 new monitoring tests) | $0.00 |
| Smoke + dev iteration on the Streamlit pages | ~$0.04 |
| First end-to-end demo run captured for the screenshots | ~$0.02 |
| **Phase 8 total** | **~$0.06** |
| Cumulative through Phase 8 | **~$0.81 / $20** budget (4%) |

## What we learned the hard way

### 1. Streamlit pages don't share `sys.path` with the entry script

`from app._helpers import ...` failed at runtime: Streamlit puts the entry script's directory on `sys.path`, not its parent. Fixes:
- The entry script: `import _helpers` (same directory).
- Pages: do their own `sys.path.insert(...)` at the top before any project imports.

The first iteration broke; the regression test is the running app.

### 2. Persona switching needs to preserve message history

Initial design rebuilt the entire `AgentSession` on persona change, blowing away the `MemorySaver`. The user lost the conversation they'd just had. Fixed in Phase 7 by adding `set_persona()` which rebuilds the agent (new prompt) but reuses the same checkpointer. Phase 8's UI exercises this — the toast says "✅ Persona switched" but the previous turns are still visible.

### 3. Headless Chrome can't capture Streamlit

`google-chrome --headless --screenshot` returns the loading shell — Streamlit content streams in via WebSocket after page load, and the snapshot fires before that. Real fix: Playwright with `wait_until="networkidle"` + a `wait_for_timeout` for the websocket render.

### 4. Alerts immediately surface a real problem

The P95 latency alert fired on the demo data — 38.5s vs. 8s target. That's the value of having the dashboard wired to actual log data: it tells us where Phase 9 needs to focus.

## What this phase still does NOT do

| Gap | Filled by |
|---|---|
| RAGAs / LLM-as-judge metrics | Phase 9 |
| Multi-seed eval runs to capture model non-determinism | Phase 9 |
| Production deployment (Streamlit Community Cloud / similar) | Future work — not in scope |
| Real-time alerting integration (Slack / email / PagerDuty) | Future work — not in scope |
