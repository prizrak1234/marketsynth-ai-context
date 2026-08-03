"""Launch Pack / Offer workflow transition guards (PRODUCT-01.1)."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.schemas.contracts import (
    LaunchPackOfferWorkflowStatus,
    OfferApprovalStatus,
    OfferArtifactStatus,
)

_VALID_WORKFLOW_TRANSITIONS: dict[
    LaunchPackOfferWorkflowStatus,
    frozenset[LaunchPackOfferWorkflowStatus],
] = {
    LaunchPackOfferWorkflowStatus.NOT_STARTED: frozenset(
        {LaunchPackOfferWorkflowStatus.REQUESTED}
    ),
    LaunchPackOfferWorkflowStatus.REQUESTED: frozenset(
        {
            LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
            LaunchPackOfferWorkflowStatus.BLOCKED_BY_VERDICT,
            LaunchPackOfferWorkflowStatus.BLOCKED_BY_EVIDENCE,
            LaunchPackOfferWorkflowStatus.BLOCKED_BY_MISSING_POSITIONING,
            LaunchPackOfferWorkflowStatus.BLOCKED_BY_CLAIMS,
        }
    ),
    LaunchPackOfferWorkflowStatus.BUILDING_OFFER: frozenset(
        {
            LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED,
            LaunchPackOfferWorkflowStatus.OFFER_GENERATION_FAILED,
        }
    ),
    LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED: frozenset(
        {
            LaunchPackOfferWorkflowStatus.OFFER_APPROVED,
            LaunchPackOfferWorkflowStatus.OFFER_REJECTED,
            LaunchPackOfferWorkflowStatus.REVISION_REQUIRED,
            LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
        }
    ),
    LaunchPackOfferWorkflowStatus.REVISION_REQUIRED: frozenset(
        {
            LaunchPackOfferWorkflowStatus.BUILDING_OFFER,
            LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED,
        }
    ),
    LaunchPackOfferWorkflowStatus.OFFER_APPROVED: frozenset(
        {LaunchPackOfferWorkflowStatus.READY_FOR_NEXT_STAGE}
    ),
}

_REVIEW_ALLOWED_VERSION_STATUSES = frozenset(
    {
        OfferArtifactStatus.REVIEW_REQUIRED,
        OfferArtifactStatus.REVISION_REQUESTED,
    }
)


def assert_workflow_transition(
    current: LaunchPackOfferWorkflowStatus,
    target: LaunchPackOfferWorkflowStatus,
) -> None:
    allowed = _VALID_WORKFLOW_TRANSITIONS.get(current, frozenset())
    if target not in allowed and current != target:
        raise InvalidStateError("invalid_workflow_transition")


def assert_review_allowed(
    *,
    version_status: OfferArtifactStatus,
    approval_status: OfferApprovalStatus,
) -> None:
    if version_status not in _REVIEW_ALLOWED_VERSION_STATUSES:
        raise InvalidStateError("invalid_review_state")
    if approval_status not in {
        OfferApprovalStatus.PENDING,
        OfferApprovalStatus.REVISION_REQUESTED,
    }:
        raise InvalidStateError("invalid_review_state")


def assert_approve_allowed(approval_status: OfferApprovalStatus) -> None:
    if approval_status == OfferApprovalStatus.REJECTED:
        raise InvalidStateError("offer_already_rejected")


def assert_not_finalized(approval_status: OfferApprovalStatus) -> None:
    if approval_status == OfferApprovalStatus.APPROVED:
        raise InvalidStateError("offer_already_approved")
