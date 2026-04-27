"""JSONL session logger — one file per session under ./logs/.

Each line is a structured record of one agent turn: user input, tool calls,
final response, latency, and token usage. Used as input to Phase 9 evaluation.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _REPO_ROOT / "logs"


@dataclass
class ToolCallRecord:
    name: str
    args: dict[str, Any]
    result_preview: str  # truncated tool output
    duration_ms: int


@dataclass
class SafetyFindingRecord:
    pattern_name: str
    severity: str
    matched_text: str


@dataclass
class TurnRecord:
    ts: float
    thread_id: str
    turn_index: int
    user_input: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    final_response: str = ""
    total_duration_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    error: str | None = None
    safety_findings: list[SafetyFindingRecord] = field(default_factory=list)


class SessionLogger:
    """Append-only JSONL logger, one file per thread_id."""

    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id
        _LOG_DIR.mkdir(exist_ok=True)
        self.path = _LOG_DIR / f"session-{thread_id}.jsonl"

    def write(self, record: TurnRecord) -> None:
        line = json.dumps(asdict(record), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def now_ms() -> int:
    return int(time.time() * 1000)
