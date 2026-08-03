"""PRODUCT-01.3B.1 — customer-safe research gap presentation tests."""

from __future__ import annotations

from uuid import uuid4

from app.business_idea_validation.gap_presentation import (
    is_internal_gap_code,
    present_research_gap,
    present_research_gaps,
)
from app.commercial_workflow.decision_branch import build_decision_branch
from app.schemas.contracts import (
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationVerdictKind,
)


def test_present_research_gap_translates_known_code() -> None:
    item = present_research_gap("fewer_than_3_fetched_sources")
    assert item.code == "fewer_than_3_fetched_sources"
    assert "тр" in item.customer_message.lower()
    assert is_internal_gap_code(item.code)
    assert item.customer_message != item.code


def test_present_research_gap_coverage_pattern() -> None:
    item = present_research_gap("coverage_competition_insufficient")
    assert "конкурент" in item.customer_message.lower()
    assert item.customer_message != "coverage_competition_insufficient"


def test_present_research_gap_business_verdict_missing() -> None:
    item = present_research_gap("business_verdict_missing")
    assert "вердикт" in item.customer_message.lower()
    assert item.intake_field is None


def test_present_research_gaps_deduplicates() -> None:
    items = present_research_gaps(
        ["missing_market_finding", "missing_market_finding", "missing_competitor_finding"],
    )
    assert len(items) == 2
    messages = {item.customer_message for item in items}
    assert all(not is_internal_gap_code(msg) for msg in messages)


def test_decision_branch_insufficient_uses_no_raw_codes() -> None:
    output = BusinessIdeaValidationOutput(
        investigation_id=uuid4(),
        business_verdict_id=None,
        research_gaps=["fewer_than_3_fetched_sources", "business_verdict_missing"],
        research_gap_items=present_research_gaps(
            ["fewer_than_3_fetched_sources", "business_verdict_missing"],
        ),
        verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        confidence=BusinessIdeaValidationConfidence(total_score=20, factors=[], penalties=[]),
        limitations=["coverage_competition_insufficient"],
    )
    branch = build_decision_branch(output)
    assert branch.launch_pack_allowed is False
    assert branch.conditions == []
    assert "fewer_than_3_fetched_sources" not in branch.explanation
    assert "coverage_competition_insufficient" not in branch.explanation
    assert branch.explanation
