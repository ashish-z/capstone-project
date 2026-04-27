"""Forbidden / suspicious patterns the safety scanner looks for in agent output.

Each pattern is a regex compiled once at import. Severity levels:
  - "high"   = blocks publication (CLI shows a warning banner)
  - "medium" = warns but allows
  - "low"    = informational
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern[str]
    severity: str  # "high" | "medium" | "low"
    description: str


# ---------------------------------------------------------------------------
# Commitment language — claims to do something the agent CANNOT do.
# These should never appear in agent output. The agent is decision-support;
# anything resembling "I will book / send / cancel" is a safety violation.
# ---------------------------------------------------------------------------

_COMMIT_VERBS = [
    # First-person committal: "I'll send / I'll book / ..."  Word-bounded to
    # avoid matching "ill" inside "will / still / until / fulfill / etc."
    r"\bi'?ll\s+(?:send|book|cancel|execute|submit|post|email|file|amend|charge|"
    r"refund|update\s+the\s+system|update\s+the\s+tms|push\s+to|notify\s+the\s+carrier)\b",
    # First-person past tense: "I have sent / I just booked / ..."
    r"\bi\s+(?:have|just)\s+(?:sent|booked|cancelled|canceled|executed|submitted|"
    r"posted|emailed|filed|amended|charged|refunded|notified)\b",
    # Active "doing it now" without subject — flag for review
    r"\b(?:sending|booking|cancelling|canceling|executing|submitting)\s+(?:it|the\s+\w+)\s+now\b",
    # Single-word completion claim on its own line: "Done." / "Sent." / etc.
    r"^\s*(?:done|sent|booked|cancelled|canceled|filed|submitted)\s*[!.]?\s*$",
]

COMMITMENT_PATTERN = Pattern(
    name="commitment_language",
    regex=re.compile("|".join(_COMMIT_VERBS), re.IGNORECASE | re.MULTILINE),
    severity="high",
    description=(
        "Agent appears to claim it took an action. The agent is decision-support "
        "only and CANNOT send, book, cancel, execute, or modify anything."
    ),
)


# ---------------------------------------------------------------------------
# Unhedged guarantees / over-promises in customer drafts.
# ---------------------------------------------------------------------------

_GUARANTEE_PHRASES = [
    # First-person commitments only — "we/I guarantee" but NOT "no guarantee"
    # or "release guarantee" (legitimate negative usage).
    r"\b(?:we|i)\s+guarantee\b",
    r"\bguaranteed\s+to\s+(?:arrive|deliver|clear|release|complete)\b",
    r"\bwe\s+(?:will\s+)?definitely\b",
    r"\bwe\s+commit\s+to\b",
    r"\bcertain(?:ly)?\s+to\s+(?:arrive|deliver|clear)\b",
    r"\bwill\s+arrive\s+on\s+\w+day\b",  # "will arrive on Friday"
]

GUARANTEE_PATTERN = Pattern(
    name="unhedged_guarantee",
    regex=re.compile("|".join(_GUARANTEE_PHRASES), re.IGNORECASE),
    severity="high",
    description=(
        "Agent used absolute / guarantee language. Customer comms must hedge "
        "(see sop-customer-comm-style-guide.md §Hedge timelines)."
    ),
)


# ---------------------------------------------------------------------------
# Hard date commitments without hedging.
# Matches "we will deliver on [date]" or "delivered by [date]" without nearby
# hedging words like "estimated", "expected", "subject to", etc.
# ---------------------------------------------------------------------------

_HARD_DATE_COMMITMENT = (
    r"\b(?:we\s+will|we'?ll|will\s+be)\s+"
    r"(?:deliver|delivered|arrive|released|cleared|completed)\s+"
    r"(?:by|on)\s+"
    r"\d{4}-\d{2}-\d{2}"
)
HARD_DATE_PATTERN = Pattern(
    name="hard_date_commitment",
    regex=re.compile(_HARD_DATE_COMMITMENT, re.IGNORECASE),
    severity="medium",
    description=(
        "Agent committed to a specific delivery / arrival / release date "
        "without hedging language. Use 'currently estimated' / "
        "'carrier-revised ETA' instead."
    ),
)


# ---------------------------------------------------------------------------
# PII / sensitive-data leak patterns. The fixtures contain only synthetic
# data, but we still defend against the agent making up or echoing things
# that *look* like PII.
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    # SSN-like
    r"\b\d{3}-\d{2}-\d{4}\b",
    # US-format phone with area-code in parens (we don't have any in fixtures)
    r"\(\d{3}\)\s*\d{3}-\d{4}",
    # Credit-card-ish (15-16 digit run)
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3,4}\b",
]
PII_PATTERN = Pattern(
    name="possible_pii",
    regex=re.compile("|".join(_PII_PATTERNS)),
    severity="medium",
    description="Output contains a string matching a PII pattern (SSN, phone, credit card).",
)


# ---------------------------------------------------------------------------
# SOP-filename mentions — collected separately because we cross-check them
# against the actual data/sops/ directory at scan time.
# ---------------------------------------------------------------------------

SOP_MENTION_REGEX = re.compile(r"sop-[a-z0-9-]+\.md", re.IGNORECASE)


ALL_PATTERNS: list[Pattern] = [
    COMMITMENT_PATTERN,
    GUARANTEE_PATTERN,
    HARD_DATE_PATTERN,
    PII_PATTERN,
]
