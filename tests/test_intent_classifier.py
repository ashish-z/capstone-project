"""Smoke tests for the embedding-based intent classifier."""

from __future__ import annotations

import pytest

from freight_copilot.memory.intent import classify


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Triage shipment FRT-1042 for me", "triage_request"),
        ("What about the alternate carrier on this lane", "follow_up"),
        ("What does our SOP say about customs holds", "policy_question"),
        ("Draft a customer email I can send", "draft_request"),
        ("Actually, the customer is Platinum tier, not Gold", "correction"),
        ("Just send the email to brookline@apparel.com for me", "commit_request"),
        ("How do you work and what tools do you have", "meta"),
    ],
)
def test_canonical_phrasings_route_correctly(text: str, expected: str) -> None:
    result = classify(text)
    assert result.intent == expected, (
        f"Misclassified {text!r} as {result.intent!r} "
        f"(expected {expected!r}; runner-up={result.runner_up}, margin={result.margin:.3f})"
    )


def test_confidence_always_in_unit_interval() -> None:
    result = classify("Triage FRT-1042")
    assert 0.0 <= result.confidence <= 1.0


def test_margin_field_is_difference_to_runner_up() -> None:
    result = classify("Triage FRT-1042")
    # By construction, margin = top_sim - runner_up_sim. It can be 0
    # for genuinely ambiguous inputs but usually positive for clear ones.
    assert result.margin >= 0.0
