"""Evidence floor enforcement tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.business_idea_validation.evidence_floors import (
    apply_floor_verdict_constraints,
    evaluate_category_floors,
)
from app.schemas.contracts import BivCommercialVerdictKind, BivEvidenceItem


def _evidence(category: str, domain: str) -> BivEvidenceItem:
    return BivEvidenceItem(
        evidence_id=uuid4(),
        source_url=f"https://{domain}.com/report",
        source_title="Report",
        accessed_at=datetime.now(UTC),
        excerpt="Substantive market observation with enough detail for validation.",
        claim_supported="Market demand signal.",
        relevance_score=0.8,
        quality_score=0.7,
        freshness_score=0.6,
        independence_group=domain,
        category=category,
        accepted=True,
    )


def test_market_floor_blocks_go() -> None:
    items = [_evidence("market", "a"), _evidence("market", "b")]
    statuses = evaluate_category_floors(items)
    market = next(s for s in statuses if s.category == "market")
    assert market.status == "insufficient"
    kind, blockers = apply_floor_verdict_constraints(BivCommercialVerdictKind.GO, statuses)
    assert kind != BivCommercialVerdictKind.GO
    assert blockers


def test_pricing_floor_caps_pilot_only() -> None:
    items = [_evidence("pricing", "price1")]
    statuses = evaluate_category_floors(items)
    kind, _ = apply_floor_verdict_constraints(BivCommercialVerdictKind.GO, statuses)
    assert kind in {BivCommercialVerdictKind.PILOT_ONLY, BivCommercialVerdictKind.HOLD}
