"""Smoke tests for the session logger — verify JSONL shape and append behaviour."""

from __future__ import annotations

import json
import time
from pathlib import Path

from freight_copilot.session_logger import (
    SessionLogger,
    ToolCallRecord,
    TurnRecord,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOG_DIR = _REPO_ROOT / "logs"


def _cleanup_thread(thread_id: str) -> None:
    target = _LOG_DIR / f"session-{thread_id}.jsonl"
    if target.exists():
        target.unlink()


def test_session_logger_writes_jsonl_per_turn() -> None:
    thread_id = "test-thread-abc"
    _cleanup_thread(thread_id)
    logger = SessionLogger(thread_id)

    logger.write(
        TurnRecord(
            ts=time.time(),
            thread_id=thread_id,
            turn_index=1,
            user_input="Triage FRT-1042",
            tool_calls=[
                ToolCallRecord(
                    name="lookup_shipment",
                    args={"shipment_id": "FRT-1042"},
                    result_preview='{"shipment_id": "FRT-1042"…}',
                    duration_ms=42,
                )
            ],
            final_response="Diagnosis: customs hold.",
            total_duration_ms=2100,
            input_tokens=1500,
            output_tokens=400,
            model="claude-haiku-4-5-20251001",
        )
    )
    logger.write(
        TurnRecord(
            ts=time.time(),
            thread_id=thread_id,
            turn_index=2,
            user_input="What's the SLA breach risk?",
            final_response="SLA breaches in 3 days.",
            total_duration_ms=900,
        )
    )

    lines = (_LOG_DIR / f"session-{thread_id}.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2

    rec1 = json.loads(lines[0])
    assert rec1["turn_index"] == 1
    assert rec1["thread_id"] == thread_id
    assert rec1["tool_calls"][0]["name"] == "lookup_shipment"
    assert rec1["input_tokens"] == 1500

    rec2 = json.loads(lines[1])
    assert rec2["turn_index"] == 2
    assert rec2["tool_calls"] == []

    _cleanup_thread(thread_id)


def teardown_module(_module: object) -> None:  # noqa: ARG001
    # Belt-and-suspenders: blow away the test thread file even if a test raised.
    test_file = _LOG_DIR / "session-test-thread-abc.jsonl"
    if test_file.exists():
        test_file.unlink()
