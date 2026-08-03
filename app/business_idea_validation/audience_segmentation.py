"""Audience segmentation subskill — internal to Business Idea Validation."""

from __future__ import annotations

from uuid import UUID

from app.business_idea_validation.coverage_plan import new_hypothesis_id
from app.business_idea_validation.extraction import sanitize_external_text
from app.schemas.contracts import (
    AudienceSegmentRecord,
    AudienceSegmentationOutput,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationInput,
)


def run_audience_segmentation(
    inp: BusinessIdeaValidationInput,
    audience_evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> AudienceSegmentationOutput:
    proposed = (inp.target_audience or "").strip()
    segments: list[AudienceSegmentRecord] = []
    hypotheses: list[str] = []
    limitations: list[str] = []

    if audience_evidence:
        for idx, ev in enumerate(audience_evidence[:3]):
            segments.append(
                AudienceSegmentRecord(
                    segment_id=f"aud-ev-{idx + 1}",
                    label=_segment_label(ev.claim, proposed),
                    needs=_extract_needs(ev.claim),
                    purchase_context=ev.supporting_excerpt[:300],
                    barriers=[],
                    price_sensitivity="unknown",
                    frequency="unknown",
                    acquisition_channels=[],
                    linked_evidence_ids=[ev.evidence_id],
                    is_hypothesis=False,
                )
            )
    elif proposed:
        seg_id = new_hypothesis_id()
        segments.append(
            AudienceSegmentRecord(
                segment_id=seg_id,
                label=proposed[:120],
                needs=["Needs validation against fetched sources."],
                purchase_context="Proposed by founder; not yet confirmed.",
                barriers=["Insufficient audience evidence."],
                price_sensitivity="unknown",
                frequency="unknown",
                acquisition_channels=[],
                linked_evidence_ids=[],
                is_hypothesis=True,
                limitations=["no_audience_evidence"],
            )
        )
        hypotheses.append(
            f"Proposed audience '{proposed[:80]}' lacks supporting evidence and remains a hypothesis."
        )
        limitations.append("audience_hypothesis_only")
    else:
        seg_id = new_hypothesis_id()
        segments.append(
            AudienceSegmentRecord(
                segment_id=seg_id,
                label="General urban consumers",
                needs=["Convenience", "Price sensitivity"],
                purchase_context="Inferred from business idea; not confirmed.",
                barriers=["Audience not specified by founder."],
                price_sensitivity="medium",
                frequency="unknown",
                acquisition_channels=["walk-in", "local discovery"],
                linked_evidence_ids=[],
                is_hypothesis=True,
                limitations=["inferred_audience"],
            )
        )
        hypotheses.append("Audience inferred from idea text without dedicated evidence.")
        limitations.append("audience_inferred")

    return AudienceSegmentationOutput(
        segments=segments,
        hypotheses=hypotheses,
        limitations=limitations,
    )


def audience_has_support(
    audience: AudienceSegmentationOutput,
    audience_evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> bool:
    from app.schemas.contracts import BivEvidenceClassification

    confirmed = [
        ev
        for ev in audience_evidence
        if ev.classification == BivEvidenceClassification.CONFIRMED
    ]
    if confirmed:
        return True
    return any(not seg.is_hypothesis for seg in audience.segments)


def _segment_label(claim: str, proposed: str) -> str:
    cleaned = sanitize_external_text(claim)[:120]
    if proposed and proposed.lower() in cleaned.lower():
        return proposed[:120]
    return cleaned[:80] or "Audience segment"


def _extract_needs(claim: str) -> list[str]:
    lower = claim.lower()
    needs: list[str] = []
    for token, label in (
        ("convenience", "Convenience"),
        ("price", "Price sensitivity"),
        ("quality", "Product quality"),
        ("speed", "Speed of service"),
        ("спрос", "Demand signal"),
        ("аудитор", "Audience relevance"),
    ):
        if token in lower:
            needs.append(label)
    return needs or ["General customer need mentioned in source."]
