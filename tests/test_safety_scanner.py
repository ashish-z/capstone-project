"""Tests for the output safety scanner."""

from __future__ import annotations

from freight_copilot.safety import scan_response


def test_clean_response_has_no_findings() -> None:
    text = (
        "Per sop-customs-hold-missing-ci.md, the customer should be notified "
        "and demurrage exposure tracked. We currently estimate release in "
        "2-4 hours pending shipper response."
    )
    report = scan_response(text)
    assert not report.has_any
    assert report.summary_line() == "safety: clean"


def test_commitment_language_flagged_high() -> None:
    text = "I'll send the email to the customer right now."
    report = scan_response(text)
    high = [f for f in report.findings if f.severity == "high"]
    assert high, "should have flagged 'I'll send'"
    assert any(f.pattern_name == "commitment_language" for f in high)


def test_done_marker_flagged() -> None:
    text = "Done."
    report = scan_response(text)
    assert any(f.pattern_name == "commitment_language" for f in report.findings)


def test_will_execute_not_flagged_as_ill_execute() -> None:
    """Regression: 'we will execute' must NOT match the 'i'll execute' pattern.

    The first run of the acceptance suite false-positived on this — the regex
    `i'?ll\\s+execute` matched the 'ill' suffix of 'will'. Word boundary fix
    should prevent it.
    """
    text = (
        "We have two options. If you wish to: (1) approve the Hapag-Lloyd "
        "re-booking — we will execute immediately and re-issue your bill of "
        "lading; or (2) accept the roll. We will submit the request once you "
        "approve. We will send the LOI template by 4pm."
    )
    report = scan_response(text)
    high = [f for f in report.findings if f.severity == "high"]
    assert not high, f"false positives: {[(f.pattern_name, f.matched_text) for f in high]}"


def test_guarantee_phrase_flagged() -> None:
    text = "We guarantee delivery by Friday."
    report = scan_response(text)
    names = [f.pattern_name for f in report.findings]
    # "guarantee" hits both unhedged_guarantee and possibly hard_date.
    assert "unhedged_guarantee" in names


def test_hard_date_commitment_flagged() -> None:
    text = "We will deliver on 2026-04-29."
    report = scan_response(text)
    assert any(f.pattern_name == "hard_date_commitment" for f in report.findings)


def test_hedged_date_not_flagged() -> None:
    text = "Carrier-revised ETA is 2026-04-29, subject to port reopening."
    report = scan_response(text)
    # Should NOT match the hard_date_commitment pattern (no "we will deliver / arrive on...")
    assert not any(f.pattern_name == "hard_date_commitment" for f in report.findings)


def test_real_sop_citation_passes() -> None:
    text = "See sop-capacity-rollover.md §Decision matrix for guidance."
    report = scan_response(text)
    assert not any(f.pattern_name == "fabricated_sop_citation" for f in report.findings)


def test_fabricated_sop_citation_flagged_high() -> None:
    text = (
        "Per sop-capacity-rollover-rebooking.md §X, you should re-book "
        "with Hapag-Lloyd."
    )
    report = scan_response(text)
    fab = [f for f in report.findings if f.pattern_name == "fabricated_sop_citation"]
    assert fab, "should have flagged the fabricated filename"
    assert fab[0].severity == "high"


def test_pii_pattern_flagged() -> None:
    text = "The contact is 555-12-3456 (SSN-format)."
    report = scan_response(text)
    assert any(f.pattern_name == "possible_pii" for f in report.findings)


def test_summary_line_aggregates_severities() -> None:
    text = (
        "I'll send the email now. We guarantee delivery on 2026-04-29. "
        "Per sop-fake.md, escalate immediately."
    )
    report = scan_response(text)
    summary = report.summary_line()
    assert summary.startswith("safety:")
    assert "high" in summary  # several high-severity findings
