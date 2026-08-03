"""Media brief status transition policy (Phase AI.52)."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.marketing.media_contracts import MediaBriefStatus

_ALLOWED_TRANSITIONS: dict[MediaBriefStatus, frozenset[MediaBriefStatus]] = {
    MediaBriefStatus.DRAFT: frozenset({MediaBriefStatus.REVIEW}),
    MediaBriefStatus.REVIEW: frozenset(
        {MediaBriefStatus.APPROVED, MediaBriefStatus.ARCHIVED},
    ),
    MediaBriefStatus.APPROVED: frozenset({MediaBriefStatus.ARCHIVED}),
    MediaBriefStatus.ARCHIVED: frozenset(),
}


def validate_media_brief_transition(
    current_status: MediaBriefStatus,
    next_status: MediaBriefStatus,
) -> None:
    if current_status == next_status:
        if next_status == MediaBriefStatus.ARCHIVED:
            raise InvalidStateError("Media brief is already archived")
        if next_status == MediaBriefStatus.APPROVED:
            raise InvalidStateError("Media brief is already approved")
        if next_status == MediaBriefStatus.REVIEW:
            raise InvalidStateError("Media brief is already in review")
        return

    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if next_status not in allowed:
        raise InvalidStateError(
            "Invalid media brief status transition: "
            f"{current_status.value} -> {next_status.value}",
        )


def assert_media_brief_can_submit_for_review(brief: object) -> None:
    status = getattr(brief, "status", None)
    if status != MediaBriefStatus.DRAFT:
        if status == MediaBriefStatus.REVIEW:
            raise InvalidStateError("Media brief is already in review")
        if status == MediaBriefStatus.ARCHIVED:
            raise InvalidStateError("Archived media briefs cannot be submitted for review")
        raise InvalidStateError("Only draft media briefs can be submitted for review")


def assert_media_brief_can_be_approved(brief: object) -> None:
    status = getattr(brief, "status", None)
    if status != MediaBriefStatus.REVIEW:
        if status == MediaBriefStatus.ARCHIVED:
            raise InvalidStateError("Archived media briefs cannot be approved")
        if status == MediaBriefStatus.APPROVED:
            raise InvalidStateError("Media brief is already approved")
        if status == MediaBriefStatus.DRAFT:
            raise InvalidStateError(
                "Draft media briefs must be submitted for review before approval",
            )
        raise InvalidStateError("Only media briefs in review can be approved")


def assert_media_brief_can_be_archived(brief: object) -> None:
    status = getattr(brief, "status", None)
    if status == MediaBriefStatus.ARCHIVED:
        raise InvalidStateError("Media brief is already archived")
    if status == MediaBriefStatus.DRAFT:
        raise InvalidStateError(
            "Draft media briefs cannot be archived; submit for review or edit first",
        )
