"""H2.8E — provider capability decision (owner-authoritative; never from unit tests)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.contracts import (
    IdentityCapabilityDecision,
    IdentityProviderCapability,
)


def classify_provider_capability(
    *,
    provider_code: str,
    supports_true_identity_mode: bool,
    supports_supporting_references: bool,
    owner_review: str | None,
    approved_failed_attempts: int = 0,
    automated_consistency: str | None = None,
    decided_by: str = "policy",
) -> IdentityCapabilityDecision:
    """Classify provider. Unit tests must never claim suitable_for_identity."""
    if decided_by == "unit_tests":
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.UNKNOWN,
            rationale="Unit tests cannot mark a provider suitable_for_identity.",
            owner_review_required=True,
            replacement_recommended=False,
            decided_by="policy",
            decided_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    review = (owner_review or "").strip().lower()
    # No owner review yet
    if not review:
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.UNKNOWN,
            rationale="No paid/real owner-reviewed qualification yet.",
            owner_review_required=True,
            replacement_recommended=False,
            decided_by=decided_by,
        )

    not_recognizable = review in {
        "not_recognizable",
        "rejected",
        "rejected_insufficient_similarity",
        "low",
        "different_person",
    }
    partial = review in {"partial", "partial_similarity", "medium", "conditionally"}
    accepted = review in {"acceptable", "recognized", "high", "accepted", "similarity_ok"}

    if not_recognizable and (
        not supports_supporting_references or approved_failed_attempts >= 2
    ):
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY,
            rationale=(
                "Correct payload + owner review still shows another person "
                "(or adapter cannot transmit sufficient references)."
            ),
            owner_review_required=False,
            replacement_recommended=True,
            decided_by="owner",
        )

    if not_recognizable and not supports_supporting_references:
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.CONDITIONALLY_SUITABLE
            if approved_failed_attempts < 2
            else IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY,
            rationale=(
                "Primary-only adapter; owner did not recognize subject. "
                "Recommend specialized identity engine if second attempt fails."
            ),
            owner_review_required=True,
            replacement_recommended=approved_failed_attempts >= 1,
            decided_by="owner",
        )

    if partial or (accepted and not supports_supporting_references):
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.CONDITIONALLY_SUITABLE,
            rationale="Recognizable in some attempts or limited to primary-only.",
            owner_review_required=True,
            replacement_recommended=False,
            decided_by="owner",
        )

    if (
        accepted
        and supports_true_identity_mode
        and supports_supporting_references
        and (automated_consistency or "") in {"high", "medium", "high_visual_consistency"}
    ):
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.SUITABLE_FOR_IDENTITY,
            rationale="Owner confirmed recognizable likeness with true identity mode.",
            owner_review_required=False,
            replacement_recommended=False,
            decided_by="owner",
        )

    if accepted:
        return IdentityCapabilityDecision(
            provider_code=provider_code,
            capability_status=IdentityProviderCapability.CONDITIONALLY_SUITABLE,
            rationale="Owner accepted likeness but adapter limits remain.",
            owner_review_required=True,
            replacement_recommended=False,
            decided_by="owner",
        )

    return IdentityCapabilityDecision(
        provider_code=provider_code,
        capability_status=IdentityProviderCapability.UNKNOWN,
        rationale="Insufficient evidence for classification.",
        owner_review_required=True,
        replacement_recommended=False,
        decided_by=decided_by,
    )
