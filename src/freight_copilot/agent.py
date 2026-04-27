"""LangGraph ReAct agent — Phase 2: basic working agent."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from freight_copilot.prompts.system import SYSTEM_PROMPT
from freight_copilot.tools.shipment_lookup import lookup_shipment

# override=True so the project's .env wins over any stale empty-valued
# env vars inherited from the parent shell. Standard for local dev.
load_dotenv(override=True)

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")


def build_agent(model: str | None = None):
    """Construct the LangGraph ReAct agent.

    Phase 2 wires a single tool (lookup_shipment); later phases add more.
    """
    llm = ChatAnthropic(
        model=model or DEFAULT_MODEL,
        temperature=0,
        max_tokens=2048,
    )
    return create_react_agent(
        model=llm,
        tools=[lookup_shipment],
        prompt=SYSTEM_PROMPT,
    )


def run_once(user_input: str, model: str | None = None) -> str:
    """Run a single-turn query against the agent. Returns the final text response."""
    agent = build_agent(model=model)
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
    final = result["messages"][-1]
    # AIMessage.content can be either a string or a list of content blocks.
    if isinstance(final.content, str):
        return final.content
    return "".join(
        block.get("text", "") for block in final.content if isinstance(block, dict)
    )
