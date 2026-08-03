"""Build findings, risks, and opportunities from evidence."""

from __future__ import annotations

from app.business_idea_validation.coverage_categories import normalize_category
from app.business_idea_validation.commercial_relevance import assess_commercial_relevance
from app.business_idea_validation.evidence_validation import clean_excerpt_for_finding
from app.schemas.contracts import (
    BivEvidenceClassification,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationOpportunity,
    BusinessIdeaValidationRisk,
    VerdictFindingType,
)


def confirmed_evidence(
    evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> list[BusinessIdeaValidationEvidenceSummary]:
    return [e for e in evidence if e.classification == BivEvidenceClassification.CONFIRMED]


def build_research_gaps(
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    limitations: list[str],
) -> list[str]:
    gaps = list(limitations)
    for item in evidence:
        if item.classification == BivEvidenceClassification.RESEARCH_GAP:
            gaps.append(item.claim or item.observation)
        elif item.classification == BivEvidenceClassification.UNSUPPORTED_CLAIM:
            for note in item.limitations:
                gaps.append(note)
    return list(dict.fromkeys(g for g in gaps if g))


def build_findings(
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    inp: BusinessIdeaValidationInput | None = None,
) -> list[BusinessIdeaValidationFinding]:
    usable = confirmed_evidence(evidence)
    if inp is not None:
        filtered: list[BusinessIdeaValidationEvidenceSummary] = []
        for item in usable:
            observation = item.observation or item.claim or ""
            if assess_commercial_relevance(
                inp=inp,
                category=item.category,
                observation=observation,
            ).relevant:
                filtered.append(item)
        usable = filtered
    by_category: dict[str, list[BusinessIdeaValidationEvidenceSummary]] = {}
    for item in usable:
        by_category.setdefault(item.category, []).append(item)

    findings: list[BusinessIdeaValidationFinding] = []
    for category, items in by_category.items():
        if not items:
            continue
        primary = items[0]
        statement = clean_excerpt_for_finding(primary.observation or primary.claim, max_len=400)
        if not statement:
            continue
        findings.append(
            BusinessIdeaValidationFinding(
                category=category,
                title=_title_for_category(category),
                statement=statement,
                linked_evidence_ids=[e.evidence_id for e in items],
                finding_type=_finding_type(category),
                is_hypothesis=False,
            )
        )
    return findings


def build_hypothesis_findings(
    evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> list[BusinessIdeaValidationFinding]:
    hypotheses = [
        e for e in evidence if e.classification == BivEvidenceClassification.HYPOTHESIS
    ]
    findings: list[BusinessIdeaValidationFinding] = []
    for item in hypotheses[:5]:
        findings.append(
            BusinessIdeaValidationFinding(
                category=item.category,
                title="Гипотеза",
                statement=item.observation or item.claim,
                linked_evidence_ids=[item.evidence_id],
                finding_type=VerdictFindingType.CONSTRAINT,
                is_hypothesis=True,
            )
        )
    return findings


def build_risks(
    evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> list[BusinessIdeaValidationRisk]:
    risks: list[BusinessIdeaValidationRisk] = []
    for item in confirmed_evidence(evidence):
        if normalize_category(item.category) != "commercial_risks":
            continue
        risks.append(
            BusinessIdeaValidationRisk(
                title=(item.observation or item.claim)[:120],
                description=item.supporting_excerpt[:500],
                severity="medium",
                linked_evidence_ids=[item.evidence_id],
            )
        )
    return risks[:5]


def build_opportunities(
    findings: list[BusinessIdeaValidationFinding],
) -> list[BusinessIdeaValidationOpportunity]:
    opportunities: list[BusinessIdeaValidationOpportunity] = []
    for finding in findings:
        if finding.category in ("market", "demand", "audience", "market_demand", "target_audience"):
            opportunities.append(
                BusinessIdeaValidationOpportunity(
                    title=f"Возможность: {finding.title}",
                    description=finding.statement[:500],
                    linked_evidence_ids=list(finding.linked_evidence_ids),
                )
            )
    return opportunities[:5]


def _title_for_category(category: str) -> str:
    from app.business_idea_validation.coverage_categories import CATEGORY_LABELS_RU, normalize_category

    canonical = normalize_category(category)
    return CATEGORY_LABELS_RU.get(canonical, canonical)


def _finding_type(category: str) -> VerdictFindingType:
    from app.business_idea_validation.coverage_categories import normalize_category

    canonical = normalize_category(category)
    if canonical == "commercial_risks":
        return VerdictFindingType.WEAKNESS
    if canonical in {"competitors", "pricing"}:
        return VerdictFindingType.CONSTRAINT
    return VerdictFindingType.STRENGTH
