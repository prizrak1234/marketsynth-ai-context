"""Agent run logging API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.api.mappers import agent_run_execute_response, agent_run_to_contract
from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    ExecutorError,
    InvalidStateError,
    NotFoundError,
    OwnershipError,
)
from app.db.models.user import UserTable
from app.executors.agent_run_coordinator import AgentRunCoordinator
from app.executors.agent_run_executor import AgentRunExecutor
from app.graphs.runner import AgentGraphRunner
from app.schemas.contracts import AgentRun, AgentRunStatus
from app.schemas.crud import (
    AgentRunCreateRequest,
    AgentRunExecuteResponse,
    AgentRunFailedRequest,
    AgentRunReplayRequest,
    AgentRunSucceededRequest,
)
from app.schemas.operational_batch import HandoffReplayBatchRequest, HandoffReplayBatchResponse
from app.schemas.workflow_summary import AgentRunWorkflowSummary
from app.services.agent_run_workflow_summary import AgentRunWorkflowSummaryService
from app.services.agent_runs import AgentRunService
from app.services.handoff_replay import HandoffReplayService
from app.services.llm_requests import LLMRequestService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.audit_contracts import ToolExecutionLogRead
from app.workers.handoff_child_worker import HandoffChildRunWorker

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.post("", response_model=AgentRun, status_code=status.HTTP_201_CREATED)
async def create_agent_run(
    body: AgentRunCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    created = await service.create_run(
        current_user.id,
        agent_id=body.agent_id,
        task_id=body.task_id,
        input_payload=body.input_payload,
        metadata=body.metadata,
        parent_agent_run_id=body.parent_agent_run_id,
    )
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent or task not found")
    return agent_run_to_contract(created)


@router.post("/handoff/replay-batch", response_model=HandoffReplayBatchResponse)
async def replay_handoff_children_batch(
    body: HandoffReplayBatchRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> HandoffReplayBatchResponse:
    service = HandoffReplayService(session)
    result = await service.replay_batch(
        current_user.id,
        body.project_id,
        limit=body.limit,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@router.post("/{run_id}/handoff/replay")
async def replay_handoff_child_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    service = HandoffReplayService(session)
    result = await service.replay_child_run(current_user.id, run_id)
    if result is None:
        run = await AgentRunService(session).get_run(current_user.id, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="handoff_run_not_replayable",
        )
    return result


@router.post("/process-handoff-children")
async def process_handoff_children(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = Query(default=5, ge=1, le=50),
) -> dict:
    settings = get_settings()
    if not settings.graph_handoff_worker_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="graph_handoff_worker_disabled",
        )
    worker = HandoffChildRunWorker(session)
    batch = await worker.process_batch(current_user.id, limit=limit)
    return batch.to_api_dict()


@router.get("", response_model=list[AgentRun])
async def list_agent_runs(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    project_id: UUID | None = Query(default=None),
    agent_id: UUID | None = Query(default=None),
    task_id: UUID | None = Query(default=None),
    status: AgentRunStatus | None = Query(default=None),
    limit: int = 100,
) -> list[AgentRun]:
    service = AgentRunService(session)
    rows = await service.list_runs(
        current_user.id,
        project_id=project_id,
        agent_id=agent_id,
        task_id=task_id,
        status=status,
        limit=limit,
    )
    return [agent_run_to_contract(row) for row in rows]


@router.get("/{run_id}", response_model=AgentRun)
async def get_agent_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    row = await service.get_run(current_user.id, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return agent_run_to_contract(row)


@router.get("/{run_id}/workflow-summary", response_model=AgentRunWorkflowSummary)
async def get_agent_run_workflow_summary(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRunWorkflowSummary:
    summary = await AgentRunWorkflowSummaryService(session).get_summary(
        current_user.id,
        run_id,
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return summary


@router.post("/{run_id}/replay", response_model=AgentRun, status_code=status.HTTP_201_CREATED)
async def replay_agent_run(
    run_id: UUID,
    body: AgentRunReplayRequest = AgentRunReplayRequest(),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    try:
        cloned = await service.replay_failed_run(
            current_user.id,
            run_id,
            replay_reason=body.reason if body is not None else None,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return agent_run_to_contract(cloned)


@router.post("/{run_id}/execute", response_model=AgentRunExecuteResponse)
async def execute_agent_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    engine: str | None = Query(default=None, description="classic or langgraph"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AgentRunExecuteResponse:
    coordinator = AgentRunCoordinator(session)
    try:
        final_run, resolved_engine = await coordinator.execute_run(
            run_id,
            current_user.id,
            request_engine=engine,
            idempotency_key=idempotency_key,
        )
    except (NotFoundError, OwnershipError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidStateError, ConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ExecutorError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return agent_run_execute_response(final_run, resolved_engine)


@router.post("/{run_id}/execute-dry-run", response_model=AgentRun)
async def execute_agent_run_dry_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    executor = AgentRunExecutor(
        session,
        AgentRunService(session),
        LLMRequestService(session),
    )
    try:
        final_run = await executor.execute_run(run_id, current_user.id)
    except (NotFoundError, OwnershipError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidStateError, ConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ExecutorError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return agent_run_to_contract(final_run)


@router.post("/{run_id}/execute-graph-dry-run", response_model=AgentRun)
async def execute_agent_run_graph_dry_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    runner = AgentGraphRunner(
        session,
        AgentRunService(session),
        LLMRequestService(session),
    )
    try:
        final_run = await runner.execute_run(run_id, current_user.id)
    except (NotFoundError, OwnershipError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidStateError, ConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ExecutorError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return agent_run_to_contract(final_run)


@router.post("/{run_id}/running", response_model=AgentRun)
async def mark_agent_run_running(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    updated = await service.mark_running(current_user.id, run_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return agent_run_to_contract(updated)


@router.post("/{run_id}/succeeded", response_model=AgentRun)
async def mark_agent_run_succeeded(
    run_id: UUID,
    body: AgentRunSucceededRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    updated = await service.mark_succeeded(current_user.id, run_id, body.output_payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return agent_run_to_contract(updated)


@router.post("/{run_id}/failed", response_model=AgentRun)
async def mark_agent_run_failed(
    run_id: UUID,
    body: AgentRunFailedRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    updated = await service.mark_failed(current_user.id, run_id, body.error)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return agent_run_to_contract(updated)


@router.post("/{run_id}/cancelled", response_model=AgentRun)
async def mark_agent_run_cancelled(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentRun:
    service = AgentRunService(session)
    updated = await service.mark_cancelled(current_user.id, run_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return agent_run_to_contract(updated)


@router.get("/{run_id}/tool-executions", response_model=list[ToolExecutionLogRead])
async def list_agent_run_tool_executions(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ToolExecutionLogRead]:
    service = ToolExecutionLogService(session)
    rows = await service.list_for_run(
        current_user.id,
        run_id,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return rows
