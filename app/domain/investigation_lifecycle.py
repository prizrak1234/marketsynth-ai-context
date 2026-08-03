"""Investigation lifecycle and stage helpers (Commercial MVP P0.2)."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.schemas.contracts import (
    InvestigationReadinessStatus,
    InvestigationStageId,
    InvestigationStageState,
    InvestigationStageStatus,
    InvestigationStatus,
)

ALL_STAGES: tuple[InvestigationStageId, ...] = tuple(InvestigationStageId)

_ALLOWED: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.DRAFT: frozenset(
        {
            InvestigationStatus.READY,
            InvestigationStatus.CANCELLED,
        }
    ),
    InvestigationStatus.READY: frozenset(
        {
            InvestigationStatus.ACTIVE,
            InvestigationStatus.BLOCKED,
            InvestigationStatus.CANCELLED,
        }
    ),
    InvestigationStatus.ACTIVE: frozenset(
        {
            InvestigationStatus.BLOCKED,
            InvestigationStatus.UNDER_REVIEW,
            InvestigationStatus.CANCELLED,
        }
    ),
    InvestigationStatus.BLOCKED: frozenset(
        {
            InvestigationStatus.READY,
            InvestigationStatus.ACTIVE,
            InvestigationStatus.CANCELLED,
        }
    ),
    InvestigationStatus.UNDER_REVIEW: frozenset(
        {
            InvestigationStatus.COMPLETED,
            InvestigationStatus.ACTIVE,
            InvestigationStatus.BLOCKED,
            InvestigationStatus.CANCELLED,
        }
    ),
    InvestigationStatus.COMPLETED: frozenset(
        {
            InvestigationStatus.SUPERSEDED,
        }
    ),
    InvestigationStatus.CANCELLED: frozenset(),
    InvestigationStatus.SUPERSEDED: frozenset(),
}


def default_stages() -> list[InvestigationStageState]:
    return [
        InvestigationStageState(
            stage_id=stage_id,
            status=InvestigationStageStatus.NOT_STARTED,
        )
        for stage_id in ALL_STAGES
    ]


def assert_transition(
    current: InvestigationStatus,
    target: InvestigationStatus,
) -> None:
    allowed = _ALLOWED.get(current, frozenset())
    if target not in allowed:
        raise InvalidStateError(
            f"investigation_invalid_transition:{current.value}->{target.value}"
        )


def compute_readiness(
    *,
    status: InvestigationStatus,
    stages: list[InvestigationStageState],
) -> tuple[InvestigationReadinessStatus, list[str]]:
    reasons: list[str] = [
        "source_domain_pending_p0_3",
        "evidence_domain_pending_p0_4",
    ]
    if status == InvestigationStatus.BLOCKED:
        return InvestigationReadinessStatus.NOT_READY, reasons + ["investigation_blocked"]
    if status == InvestigationStatus.CANCELLED:
        return InvestigationReadinessStatus.NOT_READY, reasons + ["investigation_cancelled"]
    completed = sum(
        1 for s in stages if s.status == InvestigationStageStatus.COMPLETED
    )
    if status == InvestigationStatus.UNDER_REVIEW and completed >= 6:
        return InvestigationReadinessStatus.READY_FOR_REVIEW, reasons
    if status in (
        InvestigationStatus.ACTIVE,
        InvestigationStatus.READY,
        InvestigationStatus.UNDER_REVIEW,
    ):
        return InvestigationReadinessStatus.CONDITIONALLY_READY, reasons
    return InvestigationReadinessStatus.NOT_READY, reasons
