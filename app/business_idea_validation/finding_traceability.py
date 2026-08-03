"""Finding ↔ evidence traceability validation."""

from __future__ import annotations

from app.business_idea_validation.evidence_floors import normalize_floor_category
from app.schemas.contracts import BivEvidenceItem, BivFindingItem

_HIGH_IMPACT_CATEGORIES = frozenset({"market", "pricing", "competitors", "competition", "demand"})


def source_groups_for_finding(
    finding: BivFindingItem,
    evidence_by_id: dict,
) -> list[str]:
    groups: set[str] = set()
    for eid in finding.evidence_ids:
        ev = evidence_by_id.get(eid)
        if ev is None:
            continue
        group = (ev.independence_group or ev.source_url or str(eid)).strip().lower()
        if group:
            groups.add(group)
    return sorted(groups)


def enrich_finding_source_groups(
    findings: list[BivFindingItem],
    evidence_items: list[BivEvidenceItem],
) -> list[BivFindingItem]:
    by_id = {e.evidence_id: e for e in evidence_items}
    enriched: list[BivFindingItem] = []
    for finding in findings:
        groups = source_groups_for_finding(finding, by_id)
        enriched.append(finding.model_copy(update={"source_groups": groups}))
    return enriched


def validate_finding_traceability(
    findings: list[BivFindingItem],
    evidence_items: list[BivEvidenceItem],
) -> list[str]:
    violations: list[str] = []
    accepted = {e.evidence_id: e for e in evidence_items if e.accepted}
    rejected = {e.evidence_id for e in evidence_items if not e.accepted}

    for finding in findings:
        if not finding.evidence_ids:
            violations.append(f"finding_without_evidence:{finding.finding_id}")
            continue
        for eid in finding.evidence_ids:
            if eid in rejected:
                violations.append(f"finding_uses_rejected_evidence:{finding.finding_id}")
            if eid not in accepted:
                violations.append(f"finding_unaccepted_evidence:{finding.finding_id}")

        groups = finding.source_groups or source_groups_for_finding(finding, accepted)
        cat = normalize_floor_category(finding.category)
        if cat in _HIGH_IMPACT_CATEGORIES and len(groups) < 2:
            violations.append(f"high_impact_insufficient_sources:{finding.finding_id}")

        if cat in {"market", "pricing", "competitors"}:
            for eid in finding.evidence_ids:
                ev = accepted.get(eid)
                if ev and not (ev.source_url or "").startswith("http"):
                    violations.append(f"citation_missing_url:{finding.finding_id}")

    return violations
