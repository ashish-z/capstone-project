"""Output safety scanner — runs after every agent response."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from freight_copilot.safety.patterns import (
    ALL_PATTERNS,
    SOP_MENTION_REGEX,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SOP_DIR = _REPO_ROOT / "data" / "sops"


def _real_sop_filenames() -> set[str]:
    return {p.name for p in _SOP_DIR.glob("*.md")}


@dataclass
class SafetyFinding:
    pattern_name: str
    severity: str
    description: str
    matched_text: str  # the actual matched substring
    span: tuple[int, int]  # (start, end) char offsets in the response


@dataclass
class SafetyReport:
    findings: list[SafetyFinding] = field(default_factory=list)

    @property
    def has_high_severity(self) -> bool:
        return any(f.severity == "high" for f in self.findings)

    @property
    def has_any(self) -> bool:
        return bool(self.findings)

    def summary_line(self) -> str:
        if not self.findings:
            return "safety: clean"
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        parts = [f"{n} {sev}" for sev, n in sorted(counts.items())]
        return "safety: " + ", ".join(parts)


def scan_response(text: str) -> SafetyReport:
    """Scan an agent response. Returns a structured report.

    Two scan layers:
      1. Pattern-based (commitment language, guarantees, hard dates, PII).
      2. SOP-citation cross-check — every `sop-*.md` mention must match a
         real file in data/sops/.
    """
    report = SafetyReport()

    # 1. Pattern scans
    for pattern in ALL_PATTERNS:
        for m in pattern.regex.finditer(text):
            report.findings.append(
                SafetyFinding(
                    pattern_name=pattern.name,
                    severity=pattern.severity,
                    description=pattern.description,
                    matched_text=m.group(0),
                    span=(m.start(), m.end()),
                )
            )

    # 2. SOP-citation cross-check — fabricated filenames are HIGH severity
    real = _real_sop_filenames()
    seen: set[str] = set()
    for m in SOP_MENTION_REGEX.finditer(text):
        cited = m.group(0).lower()  # filenames are stored lowercase
        if cited in seen:
            continue
        seen.add(cited)
        if cited not in real:
            report.findings.append(
                SafetyFinding(
                    pattern_name="fabricated_sop_citation",
                    severity="high",
                    description=(
                        f"Agent cited '{cited}', which does not exist in "
                        "data/sops/. This is a fabricated source citation."
                    ),
                    matched_text=m.group(0),
                    span=(m.start(), m.end()),
                )
            )

    return report
