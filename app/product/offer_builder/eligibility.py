"""Pure eligibility gate for Offer generation."""

from __future__ import annotations

from app.product.offer_builder.contracts import EligibilityResult, UpstreamBundle
from app.schemas.contracts import BusinessIdeaValidationVerdictKind, LaunchPackOfferWorkflowStatus

BIV_TO_MV: dict[BusinessIdeaValidationVerdictKind, str] = {
    BusinessIdeaValidationVerdictKind.PROCEED: "proceed",
    BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS: "proceed_with_conditions",
    BusinessIdeaValidationVerdictKind.REVISE: "revise",
    BusinessIdeaValidationVerdictKind.REJECT: "stop",
    BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE: "insufficient_evidence",
}

BLOCKER_TO_WORKFLOW: dict[str, str] = {
    "blocked_by_verdict": LaunchPackOfferWorkflowStatus.BLOCKED_BY_VERDICT.value,
    "blocked_by_evidence": LaunchPackOfferWorkflowStatus.BLOCKED_BY_EVIDENCE.value,
    "blocked_by_missing_positioning": (
        LaunchPackOfferWorkflowStatus.BLOCKED_BY_MISSING_POSITIONING.value
    ),
    "blocked_by_claims": LaunchPackOfferWorkflowStatus.BLOCKED_BY_CLAIMS.value,
    "blocked_by_missing_cim": LaunchPackOfferWorkflowStatus.BLOCKED_BY_MISSING_POSITIONING.value,
}

ALLOWED_MV_VERDICTS = frozenset({"proceed", "proceed_with_conditions"})


def map_biv_verdict_to_mv(verdict: BusinessIdeaValidationVerdictKind) -> str:
    return BIV_TO_MV[verdict]


def evaluate_eligibility(
    *,
    biv_verdict: BusinessIdeaValidationVerdictKind,
    upstream: UpstreamBundle | None,
) -> EligibilityResult:
    mv_verdict = map_biv_verdict_to_mv(biv_verdict)
    if mv_verdict not in ALLOWED_MV_VERDICTS:
        code = "blocked_by_verdict"
        if mv_verdict == "insufficient_evidence":
            code = "blocked_by_evidence"
        return EligibilityResult(allowed=False, blocker_code=code, mv_verdict=mv_verdict)

    if upstream is None:
        return EligibilityResult(
            allowed=False,
            blocker_code="blocked_by_missing_positioning",
            mv_verdict=mv_verdict,
        )

    if not upstream.positioning:
        return EligibilityResult(
            allowed=False,
            blocker_code="blocked_by_missing_positioning",
            mv_verdict=mv_verdict,
        )
    if not upstream.claim_substantiation:
        return EligibilityResult(
            allowed=False,
            blocker_code="blocked_by_claims",
            mv_verdict=mv_verdict,
        )
    if not upstream.cim or not upstream.cim.get("selected_segment_ids"):
        return EligibilityResult(
            allowed=False,
            blocker_code="blocked_by_missing_cim",
            mv_verdict=mv_verdict,
        )
    if not upstream.substantiated_claim_ids:
        return EligibilityResult(
            allowed=False,
            blocker_code="blocked_by_claims",
            mv_verdict=mv_verdict,
        )

    return EligibilityResult(allowed=True, blocker_code=None, mv_verdict=mv_verdict)
