"""Finding traceability validation tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.business_idea_validation.finding_traceability import validate_finding_traceability
from app.schemas.contracts import BivEvidenceItem, BivFindingItem


def test_finding_without_evidence_rejected() -> None:
    finding = BivFindingItem.model_construct(
        finding_id=uuid4(),
        category="market",
        claim="Market is huge.",
        interpretation="Growth",
        business_impact="High",
        evidence_ids=[],
        source_groups=[],
        confidence=0.8,
        limitations=[],
    )
    violations = validate_finding_traceability([finding], [])
    assert any("finding_without_evidence" in v for v in violations)


def test_high_impact_requires_two_source_groups() -> None:
    eid = uuid4()
    evidence = [
        BivEvidenceItem(
            evidence_id=eid,
            source_url="https://example.com/a",
            source_title="A",
            accessed_at=datetime.now(UTC),
            excerpt="Pricing benchmark data with enough detail for validation rules.",
            claim_supported="Pricing signal",
            relevance_score=0.8,
            quality_score=0.7,
            freshness_score=0.6,
            independence_group="example.com",
            category="pricing",
            accepted=True,
        )
    ]
    finding = BivFindingItem(
        finding_id=uuid4(),
        category="pricing",
        claim="Price point validated.",
        interpretation="Pricing",
        business_impact="High",
        evidence_ids=[eid],
        source_groups=["example.com"],
        confidence=0.8,
    )
    violations = validate_finding_traceability([finding], evidence)
    assert any("high_impact_insufficient_sources" in v for v in violations)
