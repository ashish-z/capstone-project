# Phase 9 — Latency profile

Profiled **4** turns from `logs/session-*.jsonl`.

## Headline

| Metric | P50 | P95 | Average | Max |
|---|---|---|---|---|
| **Total turn latency** | 35.0s | 38.6s | 31.5s | 38.6s |
| Tool wall-clock | 477ms | 565ms | 294ms | — |
| LLM wall-clock (remainder) | 34.5s | 38.1s | 31.2s | — |

**Tools account for 0.9%** of total wall-clock; **LLM accounts for 99.1%**.

Tool calls are local (Python file reads + Chroma local search), so their share is tiny — **the bottleneck is LLM round-trip time**, driven by input-token volume after Phase 6 added recall tools.

## Token volume per turn

- Avg input tokens: **6,514**  (P95: 6,850)
- Avg output tokens: **1,823**  (P95: 2,048)
- Avg tools per turn: 1.8 (max: 2)

## Per-turn detail

| Thread | Turn | Persona | Intent | Tools | Tool ms | LLM ms | Total | In tok | Out tok |
|---|---|---|---|---|---|---|---|---|---|
| `dfb5cb88` | 1 | ops_associate | triage_request | 2 | 477 | 38077 | 38.6s | 6850 | 1807 |
| `0393945d` | 1 | finance_partner | triage_request | 2 | 73 | 26604 | 26.7s | 6802 | 2048 |
| `ea7e433a` | 1 | customer_lead | triage_request | 1 | 59 | 25790 | 25.8s | 6140 | 2048 |
| `ec711a12` | 1 | ops_associate | triage_request | 2 | 565 | 34450 | 35.0s | 6266 | 1389 |

## What this means for optimization

Since LLM round-trip dominates and the bulk of the input-token cost is the system prompt + recalled SOPs being re-sent every turn, the highest-leverage interventions are (in order):

1. **Anthropic prompt caching** — the system prompt + RAG chunks are   identical across turns within a session; a 5-minute cache cuts   ~70% of the input tokens for a follow-up turn.
2. **Smaller k for `search_sops`** — k=4 produces ~2,000 input   tokens of SOP context. k=2 may suffice for many turns.
3. **Skip recall on follow-up turns** — once we've recalled customer   history once in a session, re-fetching is wasted work.
4. **Parallel tool calling** — LangGraph supports it; we currently   sequence (lookup → recall → search). Going parallel saves ~1–2s.
