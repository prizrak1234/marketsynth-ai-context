"""Tool execution audit logging service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.services.agent_runs import AgentRunService
from app.services.projects_service import ProjectService
from app.tools.audit_contracts import (
    ToolAuditTracker,
    ToolExecutionLogCreate,
    ToolExecutionLogMode,
    ToolExecutionLogRead,
    ToolExecutionLogStatus,
)
from app.tools.audit_preview import build_audit_preview
from app.tools.contracts import ToolCall, ToolExecutionContext, ToolResult
from app.tools.permissions import ToolExecutionMode


def _resolve_execution_mode(result: ToolResult) -> str:
    raw = result.metadata.get("execution_mode", ToolExecutionMode.NO_OP.value)
    if raw in {"disabled", "no_op", "read_only", "write"}:
        return raw  # type: ignore[return-value]
    return "no_op"


def _resolve_reason(result: ToolResult) -> str | None:
    reason = result.metadata.get("reason")
    if reason is not None:
        return str(reason)
    if isinstance(result.output, dict) and result.output.get("reason") is not None:
        return str(result.output["reason"])
    if isinstance(result.error, dict) and result.error.get("reason") is not None:
        return str(result.error["reason"])
    return None


class ToolExecutionLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ToolExecutionLogRepository(session)
        self._agent_runs = AgentRunService(session)
        self._projects = ProjectService(session)

    async def record_execution(
        self,
        context: ToolExecutionContext,
        tool_call: ToolCall,
        result: ToolResult,
        duration_ms: int | None,
    ) -> ToolExecutionLogRead:
        preview = build_audit_preview(tool_call, result)
        payload = ToolExecutionLogCreate(
            owner_id=context.owner_id,
            project_id=context.project_id,
            task_id=context.task_id,
            agent_id=context.agent_id,
            agent_run_id=context.agent_run_id,
            llm_request_id=context.request_id,
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            status=result.status,
            execution_mode=_resolve_execution_mode(result),
            reason=_resolve_reason(result),
            arguments_preview=preview.arguments_preview,
            result_preview=preview.result_preview,
            error_payload=preview.error_preview,
            duration_ms=duration_ms,
        )
        row = ToolExecutionLogTable(**payload.model_dump())
        created = await self._repo.create(row)
        if context.audit_tracker is not None:
            context.audit_tracker.logged_count += 1
        return _row_to_read(created)

    def note_audit_failure(self, context: ToolExecutionContext) -> None:
        if context.audit_tracker is not None:
            context.audit_tracker.failed_to_log_count += 1

    async def get_by_id(self, owner_id: UUID, log_id: UUID) -> ToolExecutionLogRead | None:
        row = await self._repo.get_by_id_for_owner(log_id, owner_id)
        if row is None:
            return None
        return _row_to_read(row)

    async def list_for_run(
        self,
        owner_id: UUID,
        run_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolExecutionLogRead] | None:
        run = await self._agent_runs.get_run(owner_id, run_id)
        if run is None:
            return None
        rows = await self._repo.list_by_run(
            owner_id,
            run_id,
            limit=limit,
            offset=offset,
        )
        return [_row_to_read(row) for row in rows]

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        tool_name: str | None = None,
        status: ToolExecutionLogStatus | None = None,
        execution_mode: ToolExecutionLogMode | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ToolExecutionLogRead] | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        rows = await self._repo.list_by_project(
            owner_id,
            project_id,
            tool_name=tool_name,
            status=status,
            execution_mode=execution_mode,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        )
        return [_row_to_read(row) for row in rows]


def _row_to_read(row: ToolExecutionLogTable) -> ToolExecutionLogRead:
    return ToolExecutionLogRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        task_id=row.task_id,
        agent_id=row.agent_id,
        agent_run_id=row.agent_run_id,
        llm_request_id=row.llm_request_id,
        tool_call_id=row.tool_call_id,
        tool_name=row.tool_name,
        status=row.status,  # type: ignore[arg-type]
        execution_mode=row.execution_mode,  # type: ignore[arg-type]
        reason=row.reason,
        arguments_preview=row.arguments_preview,
        result_preview=row.result_preview,
        error_payload=row.error_payload,
        duration_ms=row.duration_ms,
        created_at=row.created_at,
    )


def empty_audit_tracker() -> ToolAuditTracker:
    return ToolAuditTracker()
