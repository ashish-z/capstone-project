# Communication & Collaboration Guide

How this project is built, talked about, and handed off — both for the
human-AI collaboration that produced it and for anyone picking up the repo
later.

For the technical architecture, see [architecture.md](architecture.md). For
the non-technical onramp, see [project-overview.md](project-overview.md).

---

## 1. Who's involved

| Role | Who | Responsibility |
|---|---|---|
| Author / sole contributor | **Ashish Zanwar** | Design, build, eval, submission |
| Domain context | Freightify (logistics SaaS) — the author's day job | Realistic ops persona, SOPs, exception flows |
| Pair programmer | Claude (Anthropic) via Claude Code | Code generation, scaffolding, doc drafting, review |
| Reviewer | IITM Applied AI Capstone evaluator | Phase grading + final submission |

This isn't a multi-engineer project, but the human/AI collaboration is
intentional and needs its own conventions — section 4 covers those.

---

## 2. The audience for the deliverable

When this project is submitted, the reviewer should be able to answer four
questions in under 10 minutes:

1. **What problem does it solve?** → [`project-overview.md`](project-overview.md) §1.
2. **Does it work?** → run the Streamlit app, click the AT-1..AT-5 quick prompts. Or read [`docs/phase5-acceptance-results.md`](phase5-acceptance-results.md) (11/11 passed).
3. **How is it built?** → [`architecture.md`](architecture.md) (this is the technical-depth read).
4. **Was the safety story credible?** → [`docs/05-phase5-safety-and-eval.md`](05-phase5-safety-and-eval.md) plus the 6 ADV probes in `eval/adversarial_probes.yaml` (all pass).

Every doc in the repo is written so that a reviewer who reads only that doc
still knows what they need to know. There's deliberate redundancy between
the phase docs and the top-level docs — the phase docs are the build journal
(in time order, with "what we learned the hard way" sections); the top-level
docs ([overview](project-overview.md), [architecture](architecture.md),
[tech-stack](tech-stack.md), [repo-guide](repo-guide.md), this file) are
the "today" snapshot.

---

## 3. Communication conventions

### In code — comments

Comments explain **WHY** when it isn't obvious. Examples from the codebase:

```python
# override=True so the project's .env wins over any stale empty-valued
# env vars inherited from the parent shell. Standard for local dev.
load_dotenv(override=True)
```

```python
# Pinned to 1.x — torch 2.2.2 is the last x86_64 macOS build and was
# compiled against NumPy 1.x. Using NumPy 2.x triggers ABI incompat at import.
numpy>=1.26,<2.0
```

```python
# Sort longest-first so "ACME Inc Ltd." beats "ACME Inc.".
for name in sorted(candidates, key=len, reverse=True):
```

What we *don't* write: comments that paraphrase the code, comments that say
"added in Phase X", comments that name future callers, comments that turn
into stale lies after the next refactor.

### In code — tool docstrings ARE the spec

The LLM reads every tool's docstring as part of its tool spec. Docstrings
like the one in [`tools/lookup_shipment.py`](../src/freight_copilot/tools/shipment_lookup.py)
are written *for the model*, not for a human:

> *"Use this tool whenever the user mentions a shipment ID like 'FRT-1042'.
> The returned JSON is the ONLY source of truth for facts about the
> shipment; do not invent fields that aren't present."*

Edits to tool docstrings can change agent behavior. Treat them as part of
the prompt surface, not as documentation.

### In code — error handling

Trust framework guarantees and internal calls. Validate at boundaries (tool
returns, user input, file fixtures). Don't add try/except around things
that can't fail. When something legitimately could fail loudly, let it —
Pydantic `ValidationError` at the tool boundary is a feature, not a bug.

### In docs — phase writeups follow a fixed shape

Every `docs/0X-phase*.md` has the same sections, in this order:

1. **Goal** — one paragraph, what this phase moves us from / to.
2. **What's new vs. Phase N–1** — comparison table.
3. **Architecture** — ASCII diagram (text-renderable, not an image).
4. **Files added / changed** — table with file path, status, purpose.
5. **The mechanism** — how this phase's primitive actually works.
6. **Demo / acceptance results** — what passed, what's the headline.
7. **What we learned the hard way** — bugs, surprises, rejected approaches.
8. **Cost actuals** — line items + cumulative budget burn.
9. **What this phase still does NOT do** — defers to the next phase.

Reviewers should be able to start at any phase doc and find their way.

### In commit messages

Commits look like this (from `git log`):

```
phase 8: Streamlit web app + monitoring dashboard + alerts
phase 7: adaptive personas (Tech / Finance / Customer)
phase 5: safety scanner + acceptance harness (11/11 pass)
```

Phase prefix → one-line summary of *what* changed and the headline result.
Bodies (when present) explain *why* and reference the phase doc.

### In PRs

Every phase ships as one PR merged to `main`. PR description = the phase
doc's intro section. PR title matches the commit subject.

---

## 4. The human ↔ AI workflow

This codebase was built collaboratively with Claude (via Claude Code). The
workflow that worked well, and which I recommend keeping if anyone forks
this:

### What the human owns

- **Problem framing.** Phase 1 was authored by hand — the user persona, the
  AT cases, the success metrics, the budget. Everything that follows is a
  consequence of getting Phase 1 right.
- **Architectural decisions.** The "tools are read-only by design" rule, the
  composable persona prompt, "JSONL logs as single source of truth", the
  decision to not block on safety findings — these are framing choices the
  human makes, not generated.
- **Scope guard.** The biggest failure mode of an AI pair programmer is to
  build *more*. The human's job is to keep saying "no, smaller, less,
  later." Backwards-compat shims, future-proofing, and "while we're here"
  refactors are the most common drift, and the most dangerous to budget.
- **Real-data realism.** Choosing fixture details that match how exceptions
  *actually* arrive (slow shipper auto-replies; entity-suffix mismatches
  rather than legal-entity disputes; broker queue blocked rather than
  generic "delayed") — that's domain knowledge, not generated.

### What the AI does well

- Scaffolding: package layout, dataclass schemas, pytest fixtures, ruff
  config, Streamlit page wiring.
- Mechanical-but-careful work: regex with `\b` anchors, Pydantic model
  shapes, splitter parameters, ChromaDB metadata.
- Drafting docstrings and phase writeups against a clear architecture.
- Test coverage suggestions ("you didn't test the unknown-port branch").
- Catching its own past mistakes when shown the trace ("the regex matched
  'will' inside 'still' — let me anchor it").

### What the AI does badly without scope guards

- Over-engineering: feature flags, abstract base classes, "for future
  extensibility", helper modules that have one caller.
- Adding error handling for things that can't happen.
- Writing comments that paraphrase the code.
- Inventing docstrings that *sound* right but cite SOPs that don't exist
  (yes, this happened — see Phase 5 §"the scanner caught a real fabrication").

### The contract

The human writes the phase plan and the success criteria. The AI implements
against the plan, surfaces decisions it had to make, and stops at the phase
boundary. The human reviews, runs the eval suite, fixes the surprises, and
writes the phase's "what we learned the hard way".

This contract is what kept the project under $1 of LLM cost despite 8 phases
of iteration.

---

## 5. End-user communication (the agent ↔ the ops associate)

The agent's *output* has its own communication conventions, all enforced by
the system prompt + safety scanner.

### The agent's voice

- **Tactical, hedged, citable.** Not warm, not effusive. The user is
  triaging 5–15 cases; they need facts and actions, not encouragement.
- **Cite everything.** Carrier notes by timestamp; SOPs by filename + section;
  external events by source URL. If a fact has no citation, hedge or refuse.
- **Hedge timelines.** Never "we will deliver by 2026-04-29". Always
  "currently estimated", "subject to port reopening", "carrier-revised ETA".
- **Refuse cleanly.** When asked to commit an action, the agent must either
  say it can't, OR draft the artifact and explicitly hand the action back.
  "I can't send this for you, but here is the draft you can copy-paste once
  you confirm with the customer over the phone."

### Customer-comm drafts

Drafted to the customer's tier per `sop-customer-tier-comms.md`:

| Tier | Tone | Length |
|---|---|---|
| Platinum | Formal-empathetic | 4–8 paragraphs + before-send checklist |
| Gold | Formal-empathetic | 4–8 paragraphs |
| Silver | Professional | 3–5 paragraphs |
| Bronze | Direct | 2–4 paragraphs |

The `customer_lead` persona owns this — see [`personas.py`](../src/freight_copilot/prompts/personas.py).

### What the agent NEVER says

Caught by the safety scanner ([`safety/patterns.py`](../src/freight_copilot/safety/patterns.py)):

| ❌ Never | ✅ Instead |
|---|---|
| "I'll send the email" | "Once you confirm, send this email" |
| "I've booked the alternate" | "Re-booking the alternate is your call — here's the draft request to Hapag-Lloyd" |
| "We guarantee delivery" | "Currently estimated to arrive…" |
| "We will deliver on 2026-05-30" | "Carrier-revised ETA: 2026-05-30, subject to vessel cutoff" |
| Inventing an SOP filename | Citing only `sop-*.md` files that exist in `data/sops/` |
| Inventing a tracking fact | "Not in the record — would need carrier confirmation" |

---

## 6. Onboarding — picking up this repo cold

If someone (or future-me) is starting fresh:

### Day 1 — read

1. [`README.md`](../README.md) — 5 minutes. Quickstart and status table.
2. [`docs/project-overview.md`](project-overview.md) — 15 minutes. Context, persona, the 5 ATs, success metrics.
3. [`docs/architecture.md`](architecture.md) — 30 minutes. Agent loop, tools, RAG, memory, safety, monitoring.

### Day 1 — run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # then add ANTHROPIC_API_KEY

PYTHONPATH=src python -m freight_copilot.retrieval.ingest
PYTHONPATH=src python -m freight_copilot.memory.seed

PYTHONPATH=src streamlit run app/streamlit_app.py
```

Click the AT-1..AT-5 quick prompts. Click the adversarial probe. Watch the
event stream and the safety findings.

### Day 2 — orient

1. Open [`docs/repo-guide.md`](repo-guide.md). Walk every directory.
2. Read [`src/freight_copilot/agent.py`](../src/freight_copilot/agent.py)
   (~390 LOC) end-to-end. This is the spine.
3. Read [`src/freight_copilot/prompts/system.py`](../src/freight_copilot/prompts/system.py)
   and one persona addendum from
   [`personas.py`](../src/freight_copilot/prompts/personas.py). Now you
   know what the agent is told.
4. Run `pytest -q`. 85 tests pass.

### Day 3 — own a phase

Pick a phase doc. Re-run its eval script. Read the trace. Tweak something.
Re-run. Watch how the dashboard reacts.

If the next phase is Phase 9 (evaluation), the [`README.md`](../README.md)
status table marks it as ⏳ pending and the existing phase docs all close
with "what this phase still does NOT do" pointers — Phase 9 fills the
RAGAs / multi-seed / persona-stratified gaps.

---

## 7. Channels, decision logs, and links

This is a single-author project, so there's no Slack channel or wiki. The
durable record of decisions is:

| What | Where |
|---|---|
| Architectural decisions | The phase docs' "Why this design" / "What we learned the hard way" sections |
| Open questions / TODOs | The phase docs' "What this phase still does NOT do" tables |
| Risk register | [`docs/01-problem-framing.md` §8](01-problem-framing.md) |
| Cost actuals (running tally) | Each phase doc's "Cost actuals" section |
| Test counts (running tally) | Each phase doc's intro table |
| Bugs that surprised the author | The "What we learned the hard way" sections |

External services touched:

| Service | Where it shows up |
|---|---|
| Anthropic API | All LLM calls (`ANTHROPIC_API_KEY`) |
| LangSmith (optional) | If `LANGCHAIN_TRACING_V2=true`, every LangGraph run traces to `freight-ops-copilot` project |
| GitHub | Repo + per-phase PRs (`https://github.com/ashish-z/<repo>` — see `git remote -v`) |

No PII, no real customer data, no real carrier APIs. Everything is
synthetic/fixture data; the demo runs entirely on the local machine plus
the Anthropic API.

---

## 8. Submission packet

What goes to the IITM evaluator at the end:

1. **Source repo** at the merge commit on `main`.
2. **README** + the new top-level docs (this set):
   [`project-overview.md`](project-overview.md),
   [`architecture.md`](architecture.md),
   [`tech-stack.md`](tech-stack.md),
   [`repo-guide.md`](repo-guide.md),
   [`communication.md`](communication.md).
3. **Phase docs** [`01..08-phase*.md`](.) — the build journal.
4. **Acceptance results** [`phase5-acceptance-results.md`](phase5-acceptance-results.md) (the 11/11 table + per-case transcripts).
5. **Demo screenshots** [`demo_screenshots/`](../demo_screenshots/) — 3 PNGs for the 3 Streamlit pages.
6. **Captured traces** for the headline demos: AT-1 sample, AT-3 multi-turn, cross-session correction, persona compare.
7. **Phase 9 evaluation report** (when it lands) — RAGAs scores + multi-seed pass-rates.

The PDF assignment brief at the repo root is for reference only; the grading
artifact is the implementation + this set of docs.
