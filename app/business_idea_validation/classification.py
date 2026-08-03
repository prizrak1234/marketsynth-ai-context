"""PRODUCT-01.3B — evidence classification gate."""

from __future__ import annotations

from app.business_idea_validation.relevance import RelevanceAssessment
from app.business_idea_validation.source_quality import SourceQualityAssessment, source_quality_tier
from app.schemas.contracts import BivEvidenceClassification, BivSourceQualityTier


def classify_evidence_item(
    *,
    quality: SourceQualityAssessment,
    relevance: RelevanceAssessment,
    observation: str,
    is_from_search_snippet: bool = False,
) -> tuple[BivEvidenceClassification, BivSourceQualityTier, list[str]]:
    limitations: list[str] = []
    tier = source_quality_tier(quality.source_class)

    if is_from_search_snippet:
        limitations.append("search_snippet_not_evidence")
        return BivEvidenceClassification.UNSUPPORTED_CLAIM, tier, limitations

    if not observation.strip():
        limitations.append("empty_after_sanitization")
        return BivEvidenceClassification.RESEARCH_GAP, tier, limitations

    if not relevance.relevant:
        limitations.append(relevance.rationale)
        return BivEvidenceClassification.UNSUPPORTED_CLAIM, tier, limitations

    if tier == BivSourceQualityTier.D:
        limitations.append("tier_d_source_rejected")
        return BivEvidenceClassification.UNSUPPORTED_CLAIM, tier, limitations

    if tier == BivSourceQualityTier.C:
        limitations.append("tier_c_supporting_context_only")
        return BivEvidenceClassification.HYPOTHESIS, tier, limitations

    if quality.reliability_score < 0.6:
        limitations.append("low_reliability")
        return BivEvidenceClassification.HYPOTHESIS, tier, limitations

    if relevance.score < 0.25:
        limitations.append("low_relevance")
        return BivEvidenceClassification.HYPOTHESIS, tier, limitations

    return BivEvidenceClassification.CONFIRMED, tier, limitations
