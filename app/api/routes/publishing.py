"""Publishing channels and publication jobs API (Phase 6.0 — HTTP only)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    publication_delivery_log_to_contract,
    publication_job_to_contract,
    publishing_channel_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.publishing.contracts import (
    PublicationDeliveryLog,
    PublicationDeliveryLogStatus,
    PublicationJob,
    PublicationJobStatus,
    PublishingChannel,
    PublishingChannelStatus,
    PublishingChannelType,
)
from app.schemas.publishing import (
    PublicationJobCreateRequest,
    PublicationJobReplayBatchRequest,
    PublicationJobReplayBatchResponse,
    PublicationJobRescheduleRequest,
    PublishingChannelCreateRequest,
    PublishingChannelUpdateRequest,
)
from app.services.publication_calendar_service import PublicationCalendarService
from app.services.publication_delivery_log_service import PublicationDeliveryLogService
from app.services.publication_job_processor import PublicationJobProcessor
from app.services.publication_job_service import PublicationJobService
from app.services.publication_replay_service import PublicationReplayService
from app.services.publishing_channel_service import PublishingChannelService

channels_router = APIRouter(
    prefix="/projects/{project_id}/publishing-channels",
    tags=["publishing-channels"],
)

jobs_router = APIRouter(
    prefix="/projects/{project_id}/publication-jobs",
    tags=["publication-jobs"],
)

deliveries_router = APIRouter(
    prefix="/projects/{project_id}/publication-deliveries",
    tags=["publication-deliveries"],
)

calendar_router = APIRouter(
    prefix="/projects/{project_id}/publication-calendar",
    tags=["publication-calendar"],
)


@channels_router.post(
    "",
    response_model=PublishingChannel,
    status_code=status.HTTP_201_CREATED,
)
async def create_publishing_channel(
    body: PublishingChannelCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingChannel:
    service = PublishingChannelService(session)
    try:
        created = await service.create(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return publishing_channel_to_contract(created)


@channels_router.get("", response_model=list[PublishingChannel])
async def list_publishing_channels(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    channel_type: PublishingChannelType | None = Query(default=None),
    status_filter: PublishingChannelStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublishingChannel]:
    service = PublishingChannelService(session)
    rows = await service.list(
        current_user.id,
        project.id,
        include_archived=include_archived,
        channel_type=channel_type,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return [publishing_channel_to_contract(row) for row in rows]


@channels_router.get("/{channel_id}", response_model=PublishingChannel)
async def get_publishing_channel(
    channel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingChannel:
    service = PublishingChannelService(session)
    row = await service.get(current_user.id, project.id, channel_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing channel not found",
        )
    return publishing_channel_to_contract(row)


@channels_router.patch("/{channel_id}", response_model=PublishingChannel)
async def update_publishing_channel(
    channel_id: UUID,
    body: PublishingChannelUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingChannel:
    service = PublishingChannelService(session)
    try:
        updated = await service.update(current_user.id, project.id, channel_id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing channel not found",
        )
    return publishing_channel_to_contract(updated)


@channels_router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publishing_channel(
    channel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> None:
    service = PublishingChannelService(session)
    deleted = await service.delete(current_user.id, project.id, channel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing channel not found",
        )


@jobs_router.post("", response_model=PublicationJob, status_code=status.HTTP_201_CREATED)
async def create_publication_job(
    body: PublicationJobCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationJob:
    service = PublicationJobService(session)
    try:
        created = await service.create(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project, asset, or channel not found",
        )
    return publication_job_to_contract(created)


@jobs_router.get("", response_model=list[PublicationJob])
async def list_publication_jobs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    asset_id: UUID | None = Query(default=None),
    channel_id: UUID | None = Query(default=None),
    status_filter: PublicationJobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublicationJob]:
    service = PublicationJobService(session)
    rows = await service.list(
        current_user.id,
        project.id,
        asset_id=asset_id,
        channel_id=channel_id,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return [publication_job_to_contract(row) for row in rows]


@jobs_router.post("/replay-batch", response_model=PublicationJobReplayBatchResponse)
async def replay_publication_jobs_batch(
    body: PublicationJobReplayBatchRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationJobReplayBatchResponse:
    service = PublicationReplayService(session)
    result = await service.replay_batch(current_user.id, project.id, body)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return result


@jobs_router.post("/process")
async def process_publication_jobs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, int]:
    processor = PublicationJobProcessor(session)
    batch = await processor.process_batch(
        limit=limit,
        project_id=project.id,
        owner_id=project.owner_id,
    )
    return batch.to_api_dict()


@jobs_router.get("/{job_id}", response_model=PublicationJob)
async def get_publication_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationJob:
    service = PublicationJobService(session)
    row = await service.get(current_user.id, project.id, job_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication job not found",
        )
    return publication_job_to_contract(row)


@jobs_router.post("/{job_id}/replay", response_model=PublicationJob)
async def replay_publication_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationJob:
    service = PublicationReplayService(session)
    try:
        replayed = await service.replay_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if replayed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication job not found",
        )
    return publication_job_to_contract(replayed)


@jobs_router.post("/{job_id}/cancel", response_model=PublicationJob)
async def cancel_publication_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationJob:
    service = PublicationJobService(session)
    try:
        cancelled = await service.cancel(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if cancelled is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication job not found",
        )
    return publication_job_to_contract(cancelled)


@jobs_router.post("/{job_id}/reschedule", response_model=PublicationJob)
async def reschedule_publication_job(
    job_id: UUID,
    body: PublicationJobRescheduleRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationJob:
    service = PublicationJobService(session)
    try:
        updated = await service.reschedule(
            current_user.id,
            project.id,
            job_id,
            scheduled_at=body.scheduled_at,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication job not found",
        )
    return publication_job_to_contract(updated)


@deliveries_router.get("", response_model=list[PublicationDeliveryLog])
async def list_publication_deliveries(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    job_id: UUID | None = Query(default=None),
    channel_id: UUID | None = Query(default=None),
    status_filter: PublicationDeliveryLogStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PublicationDeliveryLog]:
    service = PublicationDeliveryLogService(session)
    rows = await service.list_for_project(
        current_user.id,
        project.id,
        job_id=job_id,
        channel_id=channel_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return [publication_delivery_log_to_contract(row) for row in rows]


def _require_aware_utc(value: datetime | None, *, field: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field} must be timezone-aware (UTC)",
        )
    return value.astimezone(UTC)


@calendar_router.get("")
async def get_publication_calendar(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    from_at: datetime | None = Query(default=None),
    to_at: datetime | None = Query(default=None),
    channel_id: UUID | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    status_filter: PublicationJobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    from_at = _require_aware_utc(from_at, field="from_at")
    to_at = _require_aware_utc(to_at, field="to_at")

    service = PublicationCalendarService(session)
    items = await service.list_calendar(
        current_user.id,
        project.id,
        from_at=from_at,
        to_at=to_at,
        channel_id=channel_id,
        campaign_id=campaign_id,
        status=status_filter,
        limit=limit,
    )
    return items
