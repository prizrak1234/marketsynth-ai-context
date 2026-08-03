"""PRODUCT-01.4 — commercial foundation: research quality + partial delivery."""

from __future__ import annotations

from app.business_idea_validation.extraction import extract_claims
from app.business_idea_validation.partial_research_delivery import partial_research_next_steps
from app.business_idea_validation.skill import FETCHES_PER_CATEGORY
from app.schemas.contracts import BivPartialResearchReport, BivRemediationQuestion


def test_fetch_per_category_increased_for_diversity() -> None:
    assert FETCHES_PER_CATEGORY >= 3


def test_extract_claims_fallback_returns_up_to_two_claims() -> None:
    body = (
        "This paragraph describes market growth in unrelated generic terms without category keywords. "
        "Construction SaaS adoption is accelerating among mid-size contractors in regional markets. "
        "Another independent sentence about pricing pressure in B2B software sales cycles."
    )
    claims = extract_claims(body, "unknown_category_xyz")
    assert len(claims) == 2


def test_partial_research_next_steps_not_empty_for_insufficiency() -> None:
    steps = partial_research_next_steps(
        partial_report=BivPartialResearchReport(
            established_findings=["Спрос на автоматизацию растёт в сегменте SMB."],
            probable_signals=[],
            user_hypotheses=[],
            contradictions=[],
            interim_conclusion="Частичный вывод.",
        ),
        remediation_questions=[
            BivRemediationQuestion(question="Укажите конкретных конкурентов в вашем регионе."),
        ],
        failure_code="high_impact_insufficient_sources",
    )
    assert len(steps) >= 2
    assert all(step.label.strip() for step in steps)
    assert any("уточн" in step.label.lower() or "пилот" in step.label.lower() for step in steps)


def test_partial_research_next_steps_without_evidence_still_actionable() -> None:
    steps = partial_research_next_steps(
        partial_report=None,
        remediation_questions=[],
        failure_code="finding_without_evidence",
    )
    assert len(steps) >= 2
    labels = " ".join(s.label.lower() for s in steps)
    assert "бриф" in labels or "исследован" in labels
