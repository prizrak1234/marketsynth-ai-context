"""Publication package status transition policy (Phase AI.61)."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.marketing.contracts import PublicationPackageStatus

_ALLOWED_TRANSITIONS: dict[PublicationPackageStatus, frozenset[PublicationPackageStatus]] = {
    PublicationPackageStatus.DRAFT: frozenset({PublicationPackageStatus.REVIEW}),
    PublicationPackageStatus.REVIEW: frozenset(
        {PublicationPackageStatus.APPROVED, PublicationPackageStatus.ARCHIVED},
    ),
    PublicationPackageStatus.APPROVED: frozenset({PublicationPackageStatus.ARCHIVED}),
    PublicationPackageStatus.ARCHIVED: frozenset(),
}


def validate_publication_package_transition(
    current_status: PublicationPackageStatus,
    next_status: PublicationPackageStatus,
) -> None:
    if current_status == next_status:
        if next_status == PublicationPackageStatus.ARCHIVED:
            raise InvalidStateError("Publication package is already archived")
        if next_status == PublicationPackageStatus.APPROVED:
            raise InvalidStateError("Publication package is already approved")
        if next_status == PublicationPackageStatus.REVIEW:
            raise InvalidStateError("Publication package is already in review")
        return

    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise InvalidStateError(
            "Invalid publication package status transition: "
            f"{current_status.value} -> {next_status.value}",
        )


def assert_package_can_submit_for_review(package: object) -> None:
    status = getattr(package, "status", None)
    if status != PublicationPackageStatus.DRAFT:
        if status == PublicationPackageStatus.REVIEW:
            raise InvalidStateError("Publication package is already in review")
        if status == PublicationPackageStatus.ARCHIVED:
            raise InvalidStateError("Archived publication packages cannot be submitted for review")
        raise InvalidStateError("Only draft publication packages can be submitted for review")


def assert_package_can_be_approved(package: object) -> None:
    status = getattr(package, "status", None)
    if status != PublicationPackageStatus.REVIEW:
        if status == PublicationPackageStatus.ARCHIVED:
            raise InvalidStateError("Archived publication packages cannot be approved")
        if status == PublicationPackageStatus.APPROVED:
            raise InvalidStateError("Publication package is already approved")
        if status == PublicationPackageStatus.DRAFT:
            raise InvalidStateError(
                "Draft publication packages must be submitted for review before approval",
            )
        raise InvalidStateError("Only publication packages in review can be approved")


def assert_package_can_be_archived(package: object) -> None:
    status = getattr(package, "status", None)
    if status == PublicationPackageStatus.ARCHIVED:
        raise InvalidStateError("Publication package is already archived")
    if status == PublicationPackageStatus.DRAFT:
        raise InvalidStateError(
            "Draft publication packages cannot be archived; submit for review first",
        )
