"""CWF.1 — full EvidenceItem / Finding contract mappers."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.business_idea_validation.evidence_validation import validate_evidence_acceptance
from app.business_idea_validation.finding_traceability import enrich_finding_source_groups
from app.schemas.contracts import (
    BivEvidenceItem,
    BivFindingItem,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
)


def to_evidence_item(
    summary: BusinessIdeaValidationEvidenceSummary,
) -> BivEvidenceItem:
    accepted, rejection = validate_evidence_acceptance(
        observation=summary.observation or summary.claim,
        source_url=summary.source_url,
        source_title=summary.source_title,
    )
    return BivEvidenceItem(
        evidence_id=summary.evidence_id,
        source_url=summary.source_url if accepted else summary.source_url,
        source_title=summary.source_title,
        publisher=summary.publisher,
        published_at=summary.published_at,
        accessed_at=summary.retrieved_at,
        source_type=summary.evidence_type.value,
        region=None,
        language=None,
        excerpt=(summary.supporting_excerpt or summary.observation or "")[:500],
        claim_supported=summary.claim,
        relevance_score=summary.relevance_score,
        quality_score=summary.reliability_score,
        freshness_score=summary.freshness_score,
        independence_group=summary.source_reference.domain if summary.source_reference else "",
        category=summary.category,
        accepted=accepted,
        rejection_reason=rejection,
    )


def build_evidence_items(
    summaries: list[BusinessIdeaValidationEvidenceSummary],
) -> list[BivEvidenceItem]:
    return [to_evidence_item(s) for s in summaries]


def build_finding_items(
    findings: list[BusinessIdeaValidationFinding],
    evidence_items: list[BivEvidenceItem],
) -> list[BivFindingItem]:
    accepted_ids = {e.evidence_id for e in evidence_items if e.accepted}
    items: list[BivFindingItem] = []
    for finding in findings:
        if finding.is_hypothesis:
            continue
        linked = [eid for eid in finding.linked_evidence_ids if eid in accepted_ids]
        if not linked:
            continue
        items.append(
            BivFindingItem(
                finding_id=uuid4(),
                category=finding.category,
                claim=finding.statement[:400],
                interpretation=finding.title,
                business_impact="Влияет на решение о запуске и приоритеты пилота.",
                evidence_ids=linked,
                confidence=0.65,
                limitations=[],
            )
        )
    return enrich_finding_source_groups(items, evidence_items)
