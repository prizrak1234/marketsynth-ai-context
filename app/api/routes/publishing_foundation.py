"""Publishing foundation API — channels, package jobs, metrics (AI.60–AI.64)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    publication_package_job_to_contract,
    publishing_foundation_channel_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.publishing_foundation.contracts import (
    PublicationPackageJob,
    PublishingFoundationChannel,
    PublishingFoundationChannelStatus,
    PublishingFoundationChannelType,
    PublishingFoundationMetrics,
)
from app.schemas.publishing_foundation import (
    DispatchDuePublicationJobRequest,
    PublishingFoundationChannelCreateRequest,
    PublishingFoundationChannelUpdateRequest,
    SchedulePublicationPackageJobRequest,
)
from app.services.publication_package_job_service import PublicationPackageJobService
from app.services.publishing_schedule_service import PublishingScheduleService
from app.services.publishing_foundation_channel_service import (
    PublishingFoundationChannelService,
)
from app.services.publishing_foundation_metrics_service import (
    PublishingFoundationMetricsService,
)

foundation_channels_router = APIRouter(
    prefix="/projects/{project_id}/publishing-foundation/channels",
    tags=["publishing-foundation"],
)

package_jobs_router = APIRouter(
    prefix="/projects/{project_id}/publication-package-jobs",
    tags=["publishing-foundation"],
)

metrics_router = APIRouter(
    prefix="/projects/{project_id}/publishing-foundation/metrics",
    tags=["publishing-foundation"],
)

scheduled_jobs_router = APIRouter(
    prefix="/projects/{project_id}/publishing-foundation/scheduled-jobs",
    tags=["publishing-foundation"],
)


@foundation_channels_router.post(
    "",
    response_model=PublishingFoundationChannel,
    status_code=status.HTTP_201_CREATED,
)
async def create_foundation_channel(
    body: PublishingFoundationChannelCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingFoundationChannel:
    service = PublishingFoundationChannelService(session)
    try:
        row = await service.create(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return publishing_foundation_channel_to_contract(row)


@foundation_channels_router.get("", response_model=list[PublishingFoundationChannel])
async def list_foundation_channels(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    channel_type: PublishingFoundationChannelType | None = Query(default=None),
    status_filter: PublishingFoundationChannelStatus | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublishingFoundationChannel]:
    service = PublishingFoundationChannelService(session)
    rows = await service.list(
        current_user.id,
        project.id,
        include_archived=include_archived,
        channel_type=channel_type,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [publishing_foundation_channel_to_contract(row) for row in rows]


@foundation_channels_router.get("/{channel_id}", response_model=PublishingFoundationChannel)
async def get_foundation_channel(
    channel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingFoundationChannel:
    service = PublishingFoundationChannelService(session)
    try:
        row = await service.get(current_user.id, project.id, channel_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing channel not found",
        )
    return publishing_foundation_channel_to_contract(row)


@foundation_channels_router.patch("/{channel_id}", response_model=PublishingFoundationChannel)
async def patch_foundation_channel(
    channel_id: UUID,
    body: PublishingFoundationChannelUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingFoundationChannel:
    service = PublishingFoundationChannelService(session)
    try:
        row = await service.update(current_user.id, project.id, channel_id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing channel not found",
        )
    return publishing_foundation_channel_to_contract(row)


@foundation_channels_router.post(
    "/{channel_id}/archive",
    response_model=PublishingFoundationChannel,
)
async def archive_foundation_channel(
    channel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingFoundationChannel:
    service = PublishingFoundationChannelService(session)
    try:
        row = await service.archive(current_user.id, project.id, channel_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publishing channel not found",
        )
    return publishing_foundation_channel_to_contract(row)


@package_jobs_router.get("", response_model=list[PublicationPackageJob])
async def list_publication_package_jobs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    publication_package_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublicationPackageJob]:
    service = PublicationPackageJobService(session)
    rows = await service.list_jobs(
        current_user.id,
        project.id,
        publication_package_id=publication_package_id,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [publication_package_job_to_contract(row) for row in rows]


@package_jobs_router.get("/{job_id}", response_model=PublicationPackageJob)
async def get_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    row = await service.get_job(current_user.id, project.id, job_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post(
    "/{job_id}/replay",
    response_model=PublicationPackageJob,
    status_code=status.HTTP_201_CREATED,
)
async def replay_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    try:
        row = await service.replay_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post("/{job_id}/start", response_model=PublicationPackageJob)
async def start_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    try:
        row = await service.start_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post(
    "/{job_id}/complete-dry-run",
    response_model=PublicationPackageJob,
)
async def complete_dry_run_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    try:
        row = await service.complete_dry_run(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post("/{job_id}/execute", response_model=PublicationPackageJob)
async def execute_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    try:
        row = await service.execute_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post("/{job_id}/schedule", response_model=PublicationPackageJob)
async def schedule_publication_package_job(
    job_id: UUID,
    body: SchedulePublicationPackageJobRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublishingScheduleService(session)
    try:
        row = await service.schedule_job(
            current_user.id,
            project.id,
            job_id,
            scheduled_for=body.scheduled_for,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post("/{job_id}/unschedule", response_model=PublicationPackageJob)
async def unschedule_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublishingScheduleService(session)
    try:
        row = await service.unschedule_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@package_jobs_router.post(
    "/{job_id}/execute-dry-run",
    response_model=PublicationPackageJob,
)
async def execute_dry_run_publication_package_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublicationPackageJobService(session)
    try:
        row = await service.execute_dry_run(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@scheduled_jobs_router.get("/due", response_model=list[PublicationPackageJob])
async def list_due_scheduled_publication_jobs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublicationPackageJob]:
    service = PublishingScheduleService(session)
    rows = await service.list_due_jobs(
        current_user.id,
        project.id,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [publication_package_job_to_contract(row) for row in rows]


@scheduled_jobs_router.post(
    "/{job_id}/dispatch-due",
    response_model=PublicationPackageJob,
)
async def dispatch_due_scheduled_publication_job(
    job_id: UUID,
    body: DispatchDuePublicationJobRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublicationPackageJob:
    service = PublishingScheduleService(session)
    try:
        row = await service.dispatch_due_job(
            current_user.id,
            project.id,
            job_id,
            mode=body.mode,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return publication_package_job_to_contract(row)


@metrics_router.get("", response_model=PublishingFoundationMetrics)
async def get_publishing_foundation_metrics(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PublishingFoundationMetrics:
    service = PublishingFoundationMetricsService(session)
    return await service.get_project_metrics(current_user.id, project.id)
