"""Read-only task.get tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.task_repo import TaskRepository
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.permissions import ToolExecutionMode
from app.tools.task_tools import TASK_FORBIDDEN_ARGUMENT_KEYS, TASK_GET_TOOL_NAME


@dataclass(frozen=True)
class TaskGetOptions:
    task_id: UUID
    include_metadata: bool = True


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"task.get {field_name} must be a boolean",
        tool_name=TASK_GET_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def parse_task_get_arguments(arguments: dict[str, Any]) -> TaskGetOptions:
    for forbidden_key in TASK_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"task.get does not accept argument: {forbidden_key}",
                tool_name=TASK_GET_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_task_id = arguments.get("task_id")
    if not isinstance(raw_task_id, str) or not raw_task_id.strip():
        raise ToolValidationError(
            "task.get requires a non-empty task_id string",
            tool_name=TASK_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        task_id = UUID(raw_task_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "task.get task_id must be a valid UUID",
            tool_name=TASK_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return TaskGetOptions(
        task_id=task_id,
        include_metadata=_coerce_bool(
            arguments.get("include_metadata"),
            field_name="include_metadata",
            default=True,
        ),
    )


def _validate_context(context: ToolExecutionContext) -> str | None:
    required = {
        "owner_id": context.owner_id,
        "project_id": context.project_id,
        "agent_id": context.agent_id,
        "agent_run_id": context.agent_run_id,
    }
    for field_name, value in required.items():
        if value is None:
            return f"missing_{field_name}"
    return None


def format_task_safe(row: object, *, include_metadata: bool) -> dict[str, Any]:
    updated_at = getattr(row, "completed_at", None) or row.created_at
    payload: dict[str, Any] = {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "title": row.title,
        "status": getattr(row.status, "value", str(row.status)),
        "created_at": row.created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }
    if include_metadata:
        payload["metadata"] = {}
    return payload


class TaskGetToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._tasks = TaskRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": TASK_GET_TOOL_NAME,
            "execution_mode": ToolExecutionMode.READ_ONLY,
            "request_id": context.request_id,
            "run_id": context.agent_run_id,
            "agent_id": context.agent_id,
        }

        missing_field = _validate_context(context)
        if missing_field is not None:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason=missing_field,
                error_payload={
                    "error_type": "InvalidToolContext",
                    "safe_message": "Tool execution context is incomplete",
                    "reason": missing_field,
                },
            )

        try:
            options = parse_task_get_arguments(tool_call.arguments)
        except ToolValidationError as exc:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="invalid_tool_arguments",
                error_payload={
                    "error_type": exc.error_type,
                    "safe_message": exc.safe_message,
                    "reason": "invalid_tool_arguments",
                },
            )

        row = await self._tasks.get_by_id_for_project(
            context.owner_id,
            context.project_id,
            options.task_id,
        )
        if row is None:
            existing = await self._tasks.get_by_id(options.task_id)
            if existing is None:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="task_not_found",
                    error_payload={
                        "error_type": "TaskNotFound",
                        "safe_message": "Task not found",
                        "reason": "task_not_found",
                    },
                )
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="task_access_denied",
                error_payload={
                    "error_type": "TaskAccessDenied",
                    "safe_message": "Task access denied",
                    "reason": "task_access_denied",
                },
            )

        task_payload = format_task_safe(row, include_metadata=options.include_metadata)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"task": task_payload, "count": 1},
            reason=None,
        )
