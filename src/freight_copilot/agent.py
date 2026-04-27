"""LangGraph ReAct agent — Phase 3: tools + multi-turn memory + session logging."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from freight_copilot.prompts.system import SYSTEM_PROMPT
from freight_copilot.session_logger import (
    SessionLogger,
    ToolCallRecord,
    TurnRecord,
    now_ms,
)
from freight_copilot.tools.carrier_history import carrier_history
from freight_copilot.tools.external_events import external_events
from freight_copilot.tools.search_sops import search_sops
from freight_copilot.tools.shipment_lookup import lookup_shipment

# override=True so the project's .env wins over any stale empty-valued
# env vars inherited from the parent shell. Standard for local dev.
load_dotenv(override=True)

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Data tools that ground facts about a specific shipment / carrier / port.
DATA_TOOLS = [lookup_shipment, carrier_history, external_events]
# Policy tool — RAG over the SOP corpus. Toggleable for the with-vs-without
# comparison run in Phase 4 evaluation.
RAG_TOOLS = [search_sops]
ALL_TOOLS = [*DATA_TOOLS, *RAG_TOOLS]


def build_agent(
    model: str | None = None,
    checkpointer: MemorySaver | None = None,
    use_rag: bool = True,
):
    """Construct the LangGraph ReAct agent.

    Args:
        model: Override the default Claude model.
        checkpointer: Inject a custom checkpointer (else fresh MemorySaver).
        use_rag: If False, the search_sops tool is omitted — used by the
            Phase 4 ablation run to measure RAG's contribution.
    """
    llm = ChatAnthropic(
        model=model or DEFAULT_MODEL,
        temperature=0,
        max_tokens=2048,
    )
    tools = ALL_TOOLS if use_rag else DATA_TOOLS
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer or MemorySaver(),
    )


class AgentSession:
    """A single multi-turn conversation against the agent.

    One AgentSession == one thread_id == one JSONL log file. The LangGraph
    checkpointer keeps message history in memory; the SessionLogger persists
    structured turn records for evaluation.
    """

    def __init__(
        self,
        thread_id: str | None = None,
        model: str | None = None,
        use_rag: bool = True,
    ) -> None:
        self.thread_id = thread_id or uuid.uuid4().hex[:12]
        self.model = model or DEFAULT_MODEL
        self.use_rag = use_rag
        self.checkpointer = MemorySaver()
        self.agent = build_agent(
            model=self.model,
            checkpointer=self.checkpointer,
            use_rag=use_rag,
        )
        self.logger = SessionLogger(self.thread_id)
        self._turn_index = 0
        self._config = {"configurable": {"thread_id": self.thread_id}}

    def stream_turn(self, user_input: str) -> Iterator[dict[str, Any]]:
        """Run one turn, yielding structured events for the CLI to render.

        Yields events of shape:
            {"type": "tool_call", "name": ..., "args": ...}
            {"type": "tool_result", "name": ..., "result": ...}
            {"type": "final", "text": ...}
        """
        self._turn_index += 1
        turn = TurnRecord(
            ts=time.time(),
            thread_id=self.thread_id,
            turn_index=self._turn_index,
            user_input=user_input,
            model=self.model,
        )
        turn_started_ms = now_ms()
        # Pending tool calls keyed by tool_call_id, so we can pair the AI-side
        # args with the ToolMessage when it comes back.
        pending: dict[str, dict] = {}
        final_text = ""
        last_ai_message = None

        try:
            for chunk in self.agent.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                config=self._config,
                stream_mode="values",
            ):
                msgs = chunk.get("messages", [])
                if not msgs:
                    continue
                latest = msgs[-1]

                # AI message — tool calls or final answer
                if latest.__class__.__name__ == "AIMessage":
                    last_ai_message = latest
                    if getattr(latest, "tool_calls", None):
                        for tc in latest.tool_calls:
                            pending[tc["id"]] = {
                                "name": tc["name"],
                                "args": tc.get("args", {}),
                                "started_ms": now_ms(),
                            }
                            yield {
                                "type": "tool_call",
                                "name": tc["name"],
                                "args": tc.get("args", {}),
                            }

                # Tool message — result coming back
                elif latest.__class__.__name__ == "ToolMessage":
                    info = pending.pop(
                        latest.tool_call_id,
                        {"name": latest.name, "args": {}, "started_ms": turn_started_ms},
                    )
                    duration_ms = now_ms() - info["started_ms"]
                    result_str = (
                        latest.content
                        if isinstance(latest.content, str)
                        else str(latest.content)
                    )
                    preview = result_str[:300] + ("…" if len(result_str) > 300 else "")
                    turn.tool_calls.append(
                        ToolCallRecord(
                            name=info["name"],
                            args=info["args"],
                            result_preview=preview,
                            duration_ms=duration_ms,
                        )
                    )
                    yield {
                        "type": "tool_result",
                        "name": latest.name,
                        "result": preview,
                    }

            if last_ai_message is not None:
                content = last_ai_message.content
                if isinstance(content, str):
                    final_text = content
                else:
                    final_text = "".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )
                # Token usage when available (Anthropic surfaces it on usage_metadata)
                usage = getattr(last_ai_message, "usage_metadata", None) or {}
                turn.input_tokens = usage.get("input_tokens")
                turn.output_tokens = usage.get("output_tokens")

            turn.final_response = final_text
            yield {"type": "final", "text": final_text}

        except Exception as exc:  # noqa: BLE001 — surface and log all failures
            turn.error = f"{type(exc).__name__}: {exc}"
            yield {"type": "error", "message": turn.error}
            raise
        finally:
            turn.total_duration_ms = now_ms() - turn_started_ms
            self.logger.write(turn)


def run_once(user_input: str, model: str | None = None) -> str:
    """One-shot helper for tests / scripts. Discards memory at the end."""
    session = AgentSession(model=model)
    final = ""
    for event in session.stream_turn(user_input):
        if event["type"] == "final":
            final = event["text"]
    return final
