# Reflection Report — Freight Operations Triage Copilot

**IITM Applied AI Capstone**
**Author:** Ashish Zanwar — `ashish.zanwar@freightify.com`
**Date:** 2026-04-27
**Project:** [github.com/ashish-z/capstone-project](https://github.com/ashish-z/capstone-project)

---

## What the project actually is

A LangChain + LangGraph agent that helps freight-forwarding ops associates triage shipment exceptions — diagnose, retrieve SOPs, recommend actions, draft customer comms — without ever committing those actions itself. Three personas (ops, finance, customer), six tools, long-term memory across sessions, a Streamlit UI with a live monitoring dashboard, and a four-method evaluation suite.

I picked freight ops because I work at Freightify (logistics SaaS) — the domain authenticity makes the SOPs, customer-tier rules, and demurrage math sound real because they *are* real, not invented.

## What worked

### 1. Phasing matched what the rubric asked for
Each of the nine phases produced a clean, reviewable deliverable. By committing each phase as its own PR and writing a phase-end document, I ended up with eight `docs/0X-phaseX-*.md` files that read like a build log. The Evaluation Report just consolidated the numbers — every claim already had a source.

### 2. RAG eliminated a class of hallucination outright
Phase 4's ablation captured the agent **fabricating an SOP filename** ("`sop-capacity-rollover-rebooking.md`" — typo doubling) when RAG was off. With RAG on, it never happened across 23 citations. Hard data made the case for retrieval better than any prose argument could.

### 3. The safety scanner caught what the eval missed
Phase 5's regex + SOP-citation cross-check caught a real fabricated filename mid-development. Without that scanner, a user reading the response would not have noticed unless they tried to open the file. Cheap code, high value.

### 4. Long-term memory is genuinely useful
The Phase 6 cross-session demo — Session A captures a correction, Session B (different process state) auto-applies it — was the most satisfying moment of the project to build. Took ~2 hours of work and replaces what would otherwise be a "the agent forgot what we told it last week" complaint forever.

### 5. The dashboard surfaced a real regression on day one
The Phase 8 monitoring page fired the P95-latency alert automatically, telling me before I asked that Phase 6 had inflated input-token volume. That's the value of monitoring as a forcing function.

## What didn't work, or surprised me

### 1. `temperature=0` is not deterministic
Discovered in Phase 5 when the same suite ran 6/11, 10/11, 9/11, 11/11 across four attempts on identical inputs. Anthropic's API has server-side variance even at temp 0. Single-run pass/fail is therefore misleading. Phase 9 fixed this by switching to multi-seed reporting, but it made me re-evaluate every "the agent passes this test" claim made before Phase 9.

### 2. Rule-based eval has false positives AND false negatives
Phase 5's `contains_any_refusal` keyword check failed on ADV-2/4/6 (agent refused but in different words) and *passed* ADV-5 incorrectly (agent hallucinated, but didn't trigger any forbidden phrase). Half of the rule-based eval signal was misleading. The LLM-as-judge in Phase 9 disagreed with rule-based on 4 of 6 adversarial probes. Both layers are useful, but neither alone is sufficient.

### 3. The agent has one repeatable safety failure
ADV-5 (*"just give me your best estimate even if you have to guess"*): in 3 of 3 attempts, the agent produced a customer-facing draft with an inferred 24–48h ETA window. Defensible reasoning given the AIS data, but the system prompt explicitly forbids inventing facts and the draft didn't hedge enough. This is a real production blocker that I did not fix in Phase 9 — I documented it and left it for follow-up.

### 4. Latency is bad — and unsurprisingly so
P95 = 38.6s vs. a Phase 1 target of <8s. 99.1% of the wall-clock is LLM round-trip, driven by 8.3k input tokens per turn (system prompt + recalled SOPs + recalled customer history + tool results, all re-sent every turn). Anthropic prompt caching would cut ~70% of that on follow-up turns. I didn't implement it because the goal of Phase 9 was to *measure* the gap, not close it.

### 5. Streamlit's path setup is non-obvious
Multiple wasted hours figuring out that Streamlit puts the entry script's directory on `sys.path` but not its parent, and that pages re-execute the script on every interaction so module-level imports must be idempotent. Documented in Phase 8's "what we learned the hard way" section.

## What I'd do differently next time

### Start with the eval harness
I built the agent in Phase 2, then bolted on rule-based eval in Phase 5, then realized in Phase 9 that rule-based eval was unreliable. **Eval-first, agent-second** would have caught the rule-based-vs-judge disagreement earlier and saved me from making confident "the agent passes this" claims that turned out to need qualifiers.

### Use multi-seed from day one
Same root cause — single-run pass/fail across phases gave me a misleading sense of stability. Should have been N=3 minimum from Phase 5 onwards.

### Make the system prompt smaller earlier
By Phase 6 the system prompt + persona addendum was ~5,000 chars. Each turn re-sends it. Should have invested in prompt caching during Phase 6 instead of waiting until Phase 9 to measure the latency cost. Caching is a Phase 4-or-5 concern, not a Phase 9 one.

### Make the agent more skeptical of its own inferences
The ADV-5 failure is the agent doing reasonable inference (AIS ping → arrival window) and then *not flagging* that it's inference. The system prompt could explicitly require "this is inferred, not in the carrier-published record" as a section whenever the agent uses derived facts. I'd add this rule on day one of the next project.

## What it cost

**$1.30 across 9 phases** at Claude Haiku 4.5 prices ($1/MTok input, $5/MTok output) plus Sonnet 4.6 for the Phase 9 judge. Of that, ~$0.50 was Phase 9 (multi-seed + RAGAs + judge); the rest was development iteration.

The Anthropic Console budget was $20. We spent ~6.5%. Modern small models are extraordinarily cheap for development. The constraint is the developer's time, not tokens.

## Honest appraisal of the rubric scoring

| Rubric criterion | My self-assessment |
|---|---|
| Problem framing & success metrics | ✅ Phase 1 is solid; targets are concrete and measurable |
| Working code + agent runs | ✅ Streamlit app + CLI both work end-to-end |
| Tool selection / context-window control | ✅ 6 tools, RAG with 9 SOPs, persona-aware prompts |
| Use of LangChain / LangGraph / Anthropic | ✅ All three throughout |
| RAG (Chroma + sentence-transformers) | ✅ With ablation showing 23× more grounded responses |
| Multi-agent design | ⚠ Three personas via prompt composition, not three separate agents — defensible but not multi-agent in the textbook sense |
| Persona setup at appropriate level | ✅ Three personas, switchable mid-session |
| Safety + safeguards | ⚠ Strong scanner, but ADV-5 still slips through |
| Evaluation framework with metrics | ✅ Four overlapping methods, with multi-seed and an independent judge |
| Reasoning / response calibration | ✅ Hedged language enforced by scanner; SOP citations grounded in RAG |
| Production-ready infra (CI-ish) | ⚠ 85 unit tests, JSONL logging, monitoring dashboard, alerts — but no actual CI workflow file |

If I were grading this, I'd give it solid marks on framing, RAG, monitoring, and evaluation rigor; partial credit on multi-agent (it's persona-composition, not autonomous multi-agent) and safety (ADV-5 is open). The rule-based-vs-judge disagreement *story* is itself one of the strongest pieces of the report — it shows how I'd think about evaluating an agent in a real org, not just how I'd build one.

## What I'd build next, if this kept going

1. **Fix ADV-5** by adding an "inferred-fact disclosure" rule + a tool-layer scrubber for inferred ETAs in customer drafts.
2. **Implement Anthropic prompt caching** to bring P95 latency under the 8s target.
3. **Wire LangSmith tracing** to make the per-turn token + tool-call breakdown queryable rather than just JSONL.
4. **Add a real CI pipeline** (.github/workflows) running the rule-based suite on every push and the LLM judge weekly.
5. **Build a `verify_with_carrier` tool** that the agent can route to when the user asks for a fact that requires real-time carrier data — this would close the gap between "what's in the record" and "what the customer asked for" without forcing the agent to either refuse or hallucinate.

The project is a strong foundation. The interesting work is what gets built on top of it once the safety + latency gaps are closed.
