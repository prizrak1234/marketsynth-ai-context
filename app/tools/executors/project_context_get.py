"""Read-only project_context.get tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.agent_repo import AgentRepository
from app.db.repositories.memory_repo import MemoryRepository
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.task_repo import TaskRepository
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.permissions import ToolExecutionMode
from app.tools.project_context import PROJECT_CONTEXT_GET_TOOL_NAME
from app.tools.security import sanitize_tool_payload

PROJECT_CONTEXT_MAX_TASK_LIMIT = 10
PROJECT_CONTEXT_DEFAULT_TASK_LIMIT = 5
PROJECT_CONTEXT_MAX_MEMORY_LIMIT = 10
PROJECT_CONTEXT_DEFAULT_MEMORY_LIMIT = 5
PROJECT_CONTEXT_CONTENT_PREVIEW_MAX = 160

FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "project_id",
        "owner_id",
        "agent_id",
        "agent_run_id",
        "run_id",
        "task_id",
    },
)


@dataclass(frozen=True)
class ProjectContextGetOptions:
    include_agents: bool = True
    include_recent_tasks: bool = True
    include_memory_summary: bool = False
    task_limit: int = PROJECT_CONTEXT_DEFAULT_TASK_LIMIT
    memory_limit: int = PROJECT_CONTEXT_DEFAULT_MEMORY_LIMIT


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"project_context.get {field_name} must be a boolean",
        tool_name=PROJECT_CONTEXT_GET_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def _coerce_limit(value: object, *, field_name: str, default: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int):
        raise ToolValidationError(
            f"project_context.get {field_name} must be an integer",
            tool_name=PROJECT_CONTEXT_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    if value < 1:
        raise ToolValidationError(
            f"project_context.get {field_name} must be at least 1",
            tool_name=PROJECT_CONTEXT_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    return min(value, maximum)


def parse_project_context_get_arguments(arguments: dict[str, Any]) -> ProjectContextGetOptions:
    for forbidden_key in FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"project_context.get does not accept argument: {forbidden_key}",
                tool_name=PROJECT_CONTEXT_GET_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    return ProjectContextGetOptions(
        include_agents=_coerce_bool(
            arguments.get("include_agents"),
            field_name="include_agents",
            default=True,
        ),
        include_recent_tasks=_coerce_bool(
            arguments.get("include_recent_tasks"),
            field_name="include_recent_tasks",
            default=True,
        ),
        include_memory_summary=_coerce_bool(
            arguments.get("include_memory_summary"),
            field_name="include_memory_summary",
            default=False,
        ),
        task_limit=_coerce_limit(
            arguments.get("task_limit"),
            field_name="task_limit",
            default=PROJECT_CONTEXT_DEFAULT_TASK_LIMIT,
            maximum=PROJECT_CONTEXT_MAX_TASK_LIMIT,
        ),
        memory_limit=_coerce_limit(
            arguments.get("memory_limit"),
            field_name="memory_limit",
            default=PROJECT_CONTEXT_DEFAULT_MEMORY_LIMIT,
            maximum=PROJECT_CONTEXT_MAX_MEMORY_LIMIT,
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


def _content_preview(content: str) -> str:
    sanitized = sanitize_tool_payload({"content": content}).get("content", "")
    if not isinstance(sanitized, str):
        sanitized = str(sanitized)
    if len(sanitized) <= PROJECT_CONTEXT_CONTENT_PREVIEW_MAX:
        return sanitized
    marker = "...[truncated]"
    max_body = PROJECT_CONTEXT_CONTENT_PREVIEW_MAX - len(marker)
    return f"{sanitized[:max_body]}{marker}"


def _capabilities_summary(capabilities: list[dict[str, Any]]) -> list[str]:
    summary: list[str] = []
    for capability in capabilities[:10]:
        if not isinstance(capability, dict):
            continue
        label = capability.get("name") or capability.get("id") or capability.get("type")
        if label is not None:
            summary.append(str(label))
    return summary


def _format_project(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "metadata": {},
    }


def _format_agent(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "type": getattr(row.type, "value", str(row.type)),
        "status": getattr(row.status, "value", str(row.status)),
        "name": row.name,
        "description": row.description,
        "capabilities_summary": _capabilities_summary(getattr(row, "capabilities", []) or []),
    }


def _format_task(row: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(row.id),
        "title": row.title,
        "status": getattr(row.status, "value", str(row.status)),
        "created_at": row.created_at.isoformat(),
    }
    completed_at = getattr(row, "completed_at", None)
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()
    return payload


def _format_memory_summary(row: object) -> dict[str, Any]:
    metadata = sanitize_tool_payload(getattr(row, "item_metadata", {}) or {})
    return {
        "id": str(row.id),
        "key": row.key,
        "kind": getattr(row.layer, "value", str(row.layer)),
        "created_at": row.created_at.isoformat(),
        "metadata": metadata,
        "content_preview": _content_preview(row.content),
    }


class ProjectContextGetToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._projects = ProjectRepository(session)
        self._agents = AgentRepository(session)
        self._tasks = TaskRepository(session)
        self._memory = MemoryRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": PROJECT_CONTEXT_GET_TOOL_NAME,
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
            options = parse_project_context_get_arguments(tool_call.arguments)
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

        project = await self._projects.get_by_id(context.project_id)
        if project is None or project.owner_id != context.owner_id:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="project_not_found",
                error_payload={
                    "error_type": "ProjectNotFound",
                    "safe_message": "Project not found or access denied",
                    "reason": "project_not_found",
                },
            )

        active_agents: list[dict[str, Any]] = []
        if options.include_agents:
            agent_rows = await self._agents.list_by_project(
                context.project_id,
                owner_id=context.owner_id,
                include_archived=False,
            )
            active_agents = [_format_agent(row) for row in agent_rows]

        recent_tasks: list[dict[str, Any]] = []
        if options.include_recent_tasks:
            task_rows = await self._tasks.list_recent_by_project(
                context.owner_id,
                context.project_id,
                limit=options.task_limit,
            )
            recent_tasks = [_format_task(row) for row in task_rows]

        recent_memory_summary: list[dict[str, Any]] = []
        if options.include_memory_summary:
            memory_rows = await self._memory.list_recent_by_project(
                user_id=context.owner_id,
                project_id=context.project_id,
                limit=options.memory_limit,
            )
            recent_memory_summary = [_format_memory_summary(row) for row in memory_rows]

        output_payload = {
            "project": _format_project(project),
            "active_agents": active_agents,
            "recent_tasks": recent_tasks,
            "recent_memory_summary": recent_memory_summary,
            "count": len(active_agents) + len(recent_tasks) + len(recent_memory_summary),
        }
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=output_payload,
            reason=None,
        )
