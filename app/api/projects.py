"""Projects CRUD API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    event_outbox_to_contract,
    project_to_contract,
    project_webhook_to_read,
    webhook_delivery_log_to_contract,
)
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.events.dispatcher import EventOutboxDispatcher
from app.events.outbox import EventOutboxService
from app.schemas.contracts import (
    EventOutbox,
    EventOutboxStatus,
    EventType,
    Project,
    WebhookDeliveryLog,
    WebhookDeliveryLogStatus,
)
from app.schemas.crud import (
    EventOutboxReplayResponse,
    ProjectCreate,
    ProjectCreateRequest,
    ProjectUpdate,
    ProjectWebhookCreateRequest,
    ProjectWebhookCreateResponse,
    ProjectWebhookRead,
)
from app.schemas.operational_batch import (
    EventOutboxReplayBatchRequest,
    EventOutboxReplayBatchResponse,
    WebhookDeliveryCleanupResponse,
)
from app.schemas.operational_metrics import OperationalMetricsResponse
from app.schemas.review_queue import ReviewQueueResponse
from app.services.operational_metrics_service import OperationalMetricsService
from app.services.review_queue_service import ReviewQueueService
from app.services.project_webhooks import ProjectWebhookService
from app.services.projects_service import ProjectService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.services.webhook_delivery_logs import WebhookDeliveryLogService
from app.tools.audit_contracts import (
    ToolExecutionLogMode,
    ToolExecutionLogRead,
    ToolExecutionLogStatus,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Project:
    service = ProjectService(session)
    created = await service.create(
        ProjectCreate(
            owner_id=current_user.id,
            name=body.name,
            description=body.description,
        ),
    )
    return project_to_contract(created)


@router.get("", response_model=list[Project])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    offset: int = 0,
    limit: int = 100,
) -> list[Project]:
    service = ProjectService(session)
    rows = await service.list(user_id=current_user.id, offset=offset, limit=limit)
    return [project_to_contract(row) for row in rows]


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project: ProjectTable = Depends(require_project_owner),
) -> Project:
    return project_to_contract(project)


@router.patch("/{project_id}", response_model=Project)
async def update_project(
    body: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> Project:
    service = ProjectService(session)
    updated = await service.update(project.id, body)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project_to_contract(updated)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> None:
    service = ProjectService(session)
    deleted = await service.delete(project.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/{project_id}/webhooks",
    response_model=ProjectWebhookCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_webhook(
    body: ProjectWebhookCreateRequest,
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> ProjectWebhookCreateResponse:
    service = ProjectWebhookService(session)
    created = await service.create(project.owner_id, project.id, body)
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    row, signing_secret = created
    return ProjectWebhookCreateResponse(
        webhook=project_webhook_to_read(row),
        signing_secret=signing_secret,
    )


@router.get("/{project_id}/webhooks", response_model=list[ProjectWebhookRead])
async def list_project_webhooks(
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> list[ProjectWebhookRead]:
    service = ProjectWebhookService(session)
    rows = await service.list_for_project(project.owner_id, project.id)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [project_webhook_to_read(row) for row in rows]


@router.delete("/{project_id}/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_webhook(
    webhook_id: UUID,
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> None:
    service = ProjectWebhookService(session)
    updated = await service.deactivate(project.owner_id, project.id, webhook_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


@router.post("/{project_id}/events/dispatch")
async def dispatch_project_events(
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    dispatcher = EventOutboxDispatcher(session)
    batch = await dispatcher.dispatch_batch(
        limit=limit,
        project_id=project.id,
        owner_id=project.owner_id,
    )
    return batch.to_api_dict()


@router.get("/{project_id}/webhook-deliveries", response_model=list[WebhookDeliveryLog])
async def list_project_webhook_deliveries(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    webhook_id: UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status: WebhookDeliveryLogStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[WebhookDeliveryLog]:
    service = WebhookDeliveryLogService(session)
    rows = await service.list_for_project(
        project.owner_id,
        project.id,
        webhook_id=webhook_id,
        event_type=event_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [webhook_delivery_log_to_contract(row) for row in rows]


@router.delete(
    "/{project_id}/webhook-deliveries/cleanup",
    response_model=WebhookDeliveryCleanupResponse,
)
async def cleanup_project_webhook_deliveries(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    older_than_days: int = Query(default=30, ge=7, le=365),
) -> WebhookDeliveryCleanupResponse:
    service = WebhookDeliveryLogService(session)
    deleted = await service.cleanup_old_logs(
        project.owner_id,
        project.id,
        older_than_days=older_than_days,
    )
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return WebhookDeliveryCleanupResponse(
        deleted_count=deleted,
        older_than_days=older_than_days,
    )


@router.post(
    "/{project_id}/events/replay-batch",
    response_model=EventOutboxReplayBatchResponse,
)
async def replay_project_events_batch(
    body: EventOutboxReplayBatchRequest,
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> EventOutboxReplayBatchResponse:
    service = EventOutboxService(session)
    return await service.replay_batch(
        project.owner_id,
        project.id,
        statuses=body.statuses,
        event_type=body.event_type,
        limit=body.limit,
    )


@router.post(
    "/{project_id}/events/{event_id}/replay",
    response_model=EventOutboxReplayResponse,
)
async def replay_project_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> EventOutboxReplayResponse:
    service = EventOutboxService(session)
    replayed = await service.replay_event(project.owner_id, project.id, event_id)
    if replayed is None:
        existing = await service.get_for_project(project.owner_id, project.id, event_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="event_not_replayable",
        )
    return EventOutboxReplayResponse(
        event_id=replayed.id,
        status=replayed.status.value,
        replayed=True,
    )


@router.get("/{project_id}/events", response_model=list[EventOutbox])
async def list_project_events(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    event_type: EventType | None = Query(default=None),
    status: EventOutboxStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[EventOutbox]:
    service = EventOutboxService(session)
    rows = await service.list_for_project(
        project.owner_id,
        project.id,
        event_type=event_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [event_outbox_to_contract(row) for row in rows]


@router.get("/{project_id}/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> ReviewQueueResponse:
    service = ReviewQueueService(session)
    queue = await service.get_queue(project.owner_id, project.id)
    if queue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return queue


@router.get("/{project_id}/operational-metrics", response_model=OperationalMetricsResponse)
async def get_project_operational_metrics(
    session: AsyncSession = Depends(get_session),
    project: ProjectTable = Depends(require_project_owner),
) -> OperationalMetricsResponse:
    service = OperationalMetricsService(session)
    metrics = await service.get_project_operational_metrics(project.owner_id, project.id)
    if metrics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return metrics


@router.get("/{project_id}/tool-executions", response_model=list[ToolExecutionLogRead])
async def list_project_tool_executions(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    tool_name: str | None = Query(default=None),
    status_filter: ToolExecutionLogStatus | None = Query(default=None, alias="status"),
    execution_mode: ToolExecutionLogMode | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ToolExecutionLogRead]:
    service = ToolExecutionLogService(session)
    rows = await service.list_for_project(
        current_user.id,
        project_id,
        tool_name=tool_name,
        status=status_filter,
        execution_mode=execution_mode,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return rows
