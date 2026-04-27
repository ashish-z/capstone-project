"""Tests for the persona registry and system-prompt composition."""

from __future__ import annotations

import pytest

from freight_copilot.agent import AgentSession, build_agent
from freight_copilot.prompts.personas import (
    DEFAULT_PERSONA,
    PERSONAS,
    Persona,
    get_persona,
    list_personas,
)
from freight_copilot.prompts.system import (
    BASE_SYSTEM_PROMPT,
    build_system_prompt,
)


def test_three_personas_are_registered() -> None:
    assert set(PERSONAS) == {"ops_associate", "finance_partner", "customer_lead"}


def test_default_persona_is_ops_associate() -> None:
    assert DEFAULT_PERSONA == "ops_associate"


@pytest.mark.parametrize("name", list(PERSONAS))
def test_each_persona_has_required_fields(name: str) -> None:
    p = PERSONAS[name]
    assert isinstance(p, Persona)
    assert p.role_label
    assert p.description
    assert p.addendum.strip()
    assert p.proactive_behaviors  # non-empty list


def test_get_persona_falls_back_on_unknown() -> None:
    p = get_persona("nonexistent")
    assert p.name == DEFAULT_PERSONA


def test_list_personas_returns_all_three() -> None:
    assert len(list_personas()) == 3


def test_build_system_prompt_includes_base_and_addendum() -> None:
    full = build_system_prompt("finance_partner")
    assert BASE_SYSTEM_PROMPT.strip() in full
    assert "Finance / Cost Recovery Partner" in full
    # The persona's emphasis instruction should also be in the prompt.
    assert "FINANCIAL EXPOSURE" in full


def test_personas_produce_distinguishably_different_prompts() -> None:
    """Each persona's full prompt should differ in non-trivial ways."""
    p1 = build_system_prompt("ops_associate")
    p2 = build_system_prompt("finance_partner")
    p3 = build_system_prompt("customer_lead")
    # Distinct length, distinct text.
    assert p1 != p2 != p3
    assert "FINANCIAL EXPOSURE" not in p1
    assert "FINANCIAL EXPOSURE" in p2
    assert "TONE CALIBRATION" in p3
    assert "TONE CALIBRATION" not in p1


def test_safety_rails_constant_across_personas() -> None:
    """The non-negotiable hard rules must be present in every persona prompt."""
    for name in PERSONAS:
        full = build_system_prompt(name)
        assert "Decision support only" in full
        assert "No invented facts" in full
        assert "No invented policy" in full


def test_agent_session_default_persona() -> None:
    s = AgentSession()
    assert s.persona == DEFAULT_PERSONA


def test_agent_session_explicit_persona() -> None:
    s = AgentSession(persona="finance_partner")
    assert s.persona == "finance_partner"


def test_agent_session_persona_invalid_falls_back() -> None:
    # Construction succeeds (we treat unknown as default rather than raise).
    s = AgentSession(persona="not_a_real_role")
    # The agent itself uses get_persona which falls back to default,
    # but s.persona was set to the requested string. That's fine — the
    # downstream prompt build is what matters and uses the registry.
    full_prompt = __import__(
        "freight_copilot.prompts.system", fromlist=["build_system_prompt"]
    ).build_system_prompt(s.persona)
    # Falls back to ops_associate addendum content
    assert "Operations Associate (default)" in full_prompt


def test_set_persona_switches_mid_session() -> None:
    s = AgentSession(persona="ops_associate")
    assert s.persona == "ops_associate"
    s.set_persona("finance_partner")
    assert s.persona == "finance_partner"
    s.set_persona("customer_lead")
    assert s.persona == "customer_lead"


def test_build_agent_accepts_persona_kwarg() -> None:
    # Smoke test — agent compiles with each persona.
    for name in PERSONAS:
        agent = build_agent(persona=name)
        assert agent is not None
