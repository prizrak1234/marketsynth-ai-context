"""Read-only task.list_recent tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.task_repo import TaskRepository
from app.schemas.contracts import TaskStatus
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context, format_task_safe
from app.tools.permissions import ToolExecutionMode
from app.tools.task_tools import TASK_FORBIDDEN_ARGUMENT_KEYS, TASK_LIST_RECENT_TOOL_NAME

TASK_LIST_RECENT_MAX_LIMIT = 10
TASK_LIST_RECENT_DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class TaskListRecentOptions:
    limit: int = TASK_LIST_RECENT_DEFAULT_LIMIT
    status: TaskStatus | None = None
    include_metadata: bool = False


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"task.list_recent {field_name} must be a boolean",
        tool_name=TASK_LIST_RECENT_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def _coerce_limit(value: object) -> int:
    if value is None:
        return TASK_LIST_RECENT_DEFAULT_LIMIT
    if not isinstance(value, int):
        raise ToolValidationError(
            "task.list_recent limit must be an integer",
            tool_name=TASK_LIST_RECENT_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    if value < 1:
        raise ToolValidationError(
            "task.list_recent limit must be at least 1",
            tool_name=TASK_LIST_RECENT_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    return min(value, TASK_LIST_RECENT_MAX_LIMIT)


def _coerce_status(value: object) -> TaskStatus | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            "task.list_recent status must be a non-empty string",
            tool_name=TASK_LIST_RECENT_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        return TaskStatus(value.strip().lower())
    except ValueError as exc:
        raise ToolValidationError(
            "task.list_recent status must be a valid task status",
            tool_name=TASK_LIST_RECENT_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc


def parse_task_list_recent_arguments(arguments: dict[str, Any]) -> TaskListRecentOptions:
    for forbidden_key in TASK_FORBIDDEN_ARGUMENT_KEYS | {"task_id"}:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"task.list_recent does not accept argument: {forbidden_key}",
                tool_name=TASK_LIST_RECENT_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    return TaskListRecentOptions(
        limit=_coerce_limit(arguments.get("limit")),
        status=_coerce_status(arguments.get("status")),
        include_metadata=_coerce_bool(
            arguments.get("include_metadata"),
            field_name="include_metadata",
            default=False,
        ),
    )


class TaskListRecentToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._tasks = TaskRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": TASK_LIST_RECENT_TOOL_NAME,
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
            options = parse_task_list_recent_arguments(tool_call.arguments)
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

        rows = await self._tasks.list_recent_by_project(
            context.owner_id,
            context.project_id,
            limit=options.limit,
            status=options.status,
        )
        items = [
            format_task_safe(row, include_metadata=options.include_metadata) for row in rows
        ]
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"items": items, "count": len(items)},
            reason=None,
        )
