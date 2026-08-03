"""String status values for BIV runs — aligned with Alembic VARCHAR(32) storage."""

from __future__ import annotations

from app.schemas.contracts import BusinessIdeaValidationRunStatus

BIV_RUN_STATUS_QUEUED: str = BusinessIdeaValidationRunStatus.QUEUED.value
BIV_RUN_STATUS_RUNNING: str = BusinessIdeaValidationRunStatus.RUNNING.value
BIV_RUN_STATUS_SUCCEEDED: str = BusinessIdeaValidationRunStatus.SUCCEEDED.value
BIV_RUN_STATUS_FAILED: str = BusinessIdeaValidationRunStatus.FAILED.value

BIV_RUN_ACTIVE_STATUSES: tuple[str, ...] = (
    BIV_RUN_STATUS_QUEUED,
    BIV_RUN_STATUS_RUNNING,
)
