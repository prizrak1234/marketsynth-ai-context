"""Deterministic confidence calculation for CMVP.1.1."""

from __future__ import annotations

from app.business_idea_validation.source_quality import count_independent_groups
from app.schemas.contracts import (
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationConfidenceFactor,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationSourceSummary,
)

CALCULATION_VERSION = "cmvp1_1_v1"

_WEIGHTS = {
    "coverage": 0.25,
    "independence": 0.20,
    "reliability": 0.20,
    "freshness": 0.15,
    "contradictions": 0.10,
    "assumptions": 0.10,
}


def calculate_confidence(
    *,
    sources: list[BusinessIdeaValidationSourceSummary],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    contradiction_count: int,
    unresolved_assumption_count: int,
    gate_passed: bool,
) -> BusinessIdeaValidationConfidence:
    penalties: list[str] = []
    if not gate_passed:
        penalties.append("coverage_gate_not_met")

    fetched_count = len(sources)
    coverage_score = min(1.0, fetched_count / 3.0)

    independent_groups = count_independent_groups(sources)
    independence_score = min(1.0, len(independent_groups) / 3.0) if independent_groups else 0.0

    if evidence:
        reliability_score = sum(e.reliability_score for e in evidence) / len(evidence)
        freshness_score = sum(e.freshness_score for e in evidence) / len(evidence)
    else:
        reliability_score = 0.0
        freshness_score = 0.0

    contradiction_penalty = min(1.0, contradiction_count * 0.25)
    contradictions_score = max(0.0, 1.0 - contradiction_penalty)
    if contradiction_count:
        penalties.append(f"contradictions:{contradiction_count}")

    assumptions_score = max(0.0, 1.0 - min(1.0, unresolved_assumption_count * 0.2))
    if unresolved_assumption_count:
        penalties.append(f"unresolved_assumptions:{unresolved_assumption_count}")

    raw_scores = {
        "coverage": coverage_score,
        "independence": independence_score,
        "reliability": reliability_score,
        "freshness": freshness_score,
        "contradictions": contradictions_score,
        "assumptions": assumptions_score,
    }

    factors: list[BusinessIdeaValidationConfidenceFactor] = []
    total = 0.0
    for name, weight in _WEIGHTS.items():
        score = raw_scores[name]
        weighted = score * weight
        total += weighted
        factors.append(
            BusinessIdeaValidationConfidenceFactor(
                name=name,
                score=round(score, 4),
                weight=weight,
                weighted_score=round(weighted, 4),
            )
        )

    if not gate_passed:
        total = min(total, 0.35)

    return BusinessIdeaValidationConfidence(
        total_score=int(round(total * 100)),
        calculation_version=CALCULATION_VERSION,
        factors=factors,
        penalties=penalties,
    )
