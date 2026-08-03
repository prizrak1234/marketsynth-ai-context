"""Content asset status transition policy (Phase 4.3 / AI.42).

Content Factory reject-from-draft uses draft -> archived.
"""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.marketing.contracts import ContentAssetStatus

_ALLOWED_TRANSITIONS: dict[ContentAssetStatus, frozenset[ContentAssetStatus]] = {
    ContentAssetStatus.DRAFT: frozenset(
        {ContentAssetStatus.REVIEW, ContentAssetStatus.ARCHIVED},
    ),
    ContentAssetStatus.REVIEW: frozenset(
        {ContentAssetStatus.APPROVED, ContentAssetStatus.ARCHIVED},
    ),
    ContentAssetStatus.APPROVED: frozenset({ContentAssetStatus.ARCHIVED}),
    ContentAssetStatus.ARCHIVED: frozenset(),
}


def validate_content_asset_transition(
    current_status: ContentAssetStatus,
    next_status: ContentAssetStatus,
) -> None:
    if current_status == next_status:
        if next_status == ContentAssetStatus.ARCHIVED:
            raise InvalidStateError("Content asset is already archived")
        if next_status == ContentAssetStatus.APPROVED:
            raise InvalidStateError("Content asset is already approved")
        if next_status == ContentAssetStatus.REVIEW:
            raise InvalidStateError("Content asset is already in review")
        return

    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise InvalidStateError(
            "Invalid content asset status transition: "
            f"{current_status.value} -> {next_status.value}",
        )


def assert_asset_content_editable(asset: object) -> None:
    status = getattr(asset, "status", None)
    if status in (ContentAssetStatus.APPROVED, ContentAssetStatus.REVIEW):
        raise InvalidStateError(
            "Content in review or approved cannot be edited in place; "
            "create a revision after approval",
        )
    if status == ContentAssetStatus.ARCHIVED:
        raise InvalidStateError("Archived content assets cannot be edited")


def assert_asset_can_create_revision(asset: object) -> None:
    status = getattr(asset, "status", None)
    if status == ContentAssetStatus.ARCHIVED:
        raise InvalidStateError("Archived content assets cannot create revisions")
    if status == ContentAssetStatus.DRAFT:
        raise InvalidStateError("Only approved content assets can create revisions")
    if status == ContentAssetStatus.REVIEW:
        raise InvalidStateError(
            "Content assets in review cannot create revisions; approve or archive first",
        )
    if status != ContentAssetStatus.APPROVED:
        raise InvalidStateError("Only approved content assets can create revisions")

    approved_version_number = getattr(asset, "approved_version_number", None)
    if approved_version_number is None:
        raise InvalidStateError(
            "Content asset has no approved version to create a revision from",
        )


def assert_asset_can_create_rollback_revision(
    asset: object,
    _source_version_number: int,
) -> None:
    status = getattr(asset, "status", None)
    if status == ContentAssetStatus.ARCHIVED:
        raise InvalidStateError(
            "Archived content assets cannot create rollback revisions",
        )
    if status == ContentAssetStatus.DRAFT:
        raise InvalidStateError(
            "Only approved content assets can create rollback revisions",
        )
    if status == ContentAssetStatus.REVIEW:
        raise InvalidStateError(
            "Content assets in review cannot create rollback revisions",
        )
    if status != ContentAssetStatus.APPROVED:
        raise InvalidStateError(
            "Only approved content assets can create rollback revisions",
        )


def assert_asset_can_submit_for_review(asset: object) -> None:
    status = getattr(asset, "status", None)
    if status != ContentAssetStatus.DRAFT:
        if status == ContentAssetStatus.REVIEW:
            raise InvalidStateError("Content asset is already in review")
        if status == ContentAssetStatus.ARCHIVED:
            raise InvalidStateError("Archived content assets cannot be submitted for review")
        raise InvalidStateError("Only draft content assets can be submitted for review")


def assert_asset_can_be_approved(asset: object) -> None:
    status = getattr(asset, "status", None)
    if status != ContentAssetStatus.REVIEW:
        if status == ContentAssetStatus.ARCHIVED:
            raise InvalidStateError("Archived content assets cannot be approved")
        if status == ContentAssetStatus.APPROVED:
            raise InvalidStateError("Content asset is already approved")
        if status == ContentAssetStatus.DRAFT:
            raise InvalidStateError(
                "Draft content assets must be submitted for review before approval",
            )
        raise InvalidStateError("Only content assets in review can be approved")


def assert_asset_can_be_archived(asset: object) -> None:
    status = getattr(asset, "status", None)
    if status == ContentAssetStatus.ARCHIVED:
        raise InvalidStateError("Content asset is already archived")
