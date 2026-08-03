"""Read-only memory.search tool executor."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.memory_service import MemoryService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import (
    ToolExecutionResult,
    ToolExecutionStatus,
)
from app.tools.permissions import ToolExecutionMode
from app.tools.security import sanitize_tool_payload

MEMORY_SEARCH_MAX_LIMIT = 20
MEMORY_SEARCH_DEFAULT_LIMIT = 5


def parse_memory_search_arguments(arguments: dict[str, Any]) -> tuple[str, UUID | None, int]:
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ToolValidationError(
            "memory.search requires a non-empty query string",
            tool_name="memory.search",
            original_error_type="InvalidToolArguments",
        )

    agent_id: UUID | None = None
    raw_agent_id = arguments.get("agent_id")
    if raw_agent_id is not None:
        if not isinstance(raw_agent_id, str):
            raise ToolValidationError(
                "memory.search agent_id must be a string UUID",
                tool_name="memory.search",
                original_error_type="InvalidToolArguments",
            )
        try:
            agent_id = UUID(raw_agent_id)
        except ValueError as exc:
            raise ToolValidationError(
                "memory.search agent_id must be a valid UUID",
                tool_name="memory.search",
                original_error_type="InvalidToolArguments",
            ) from exc

    limit = arguments.get("limit", MEMORY_SEARCH_DEFAULT_LIMIT)
    if not isinstance(limit, int):
        raise ToolValidationError(
            "memory.search limit must be an integer",
            tool_name="memory.search",
            original_error_type="InvalidToolArguments",
        )
    if limit < 1:
        raise ToolValidationError(
            "memory.search limit must be at least 1",
            tool_name="memory.search",
            original_error_type="InvalidToolArguments",
        )

    return query.strip(), agent_id, min(limit, MEMORY_SEARCH_MAX_LIMIT)


MEMORY_SEARCH_CONTENT_PREVIEW_MAX = 160


def _content_preview(content: str) -> str:
    sanitized = sanitize_tool_payload({"content": content}).get("content", "")
    if not isinstance(sanitized, str):
        sanitized = str(sanitized)
    if len(sanitized) <= MEMORY_SEARCH_CONTENT_PREVIEW_MAX:
        return sanitized
    marker = "...[truncated]"
    max_body = MEMORY_SEARCH_CONTENT_PREVIEW_MAX - len(marker)
    return f"{sanitized[:max_body]}{marker}"


def _format_memory_item(row: object) -> dict[str, Any]:
    metadata = sanitize_tool_payload(getattr(row, "item_metadata", {}) or {})
    return {
        "id": str(row.id),
        "kind": getattr(row.layer, "value", str(row.layer)),
        "content_preview": _content_preview(row.content),
        "metadata": metadata,
        "created_at": row.created_at.isoformat(),
    }


class MemorySearchToolExecutor:
    def __init__(self, memory_service: MemoryService) -> None:
        self._memory = memory_service

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": "memory.search",
            "execution_mode": ToolExecutionMode.READ_ONLY,
            "request_id": context.request_id,
            "run_id": context.agent_run_id,
            "agent_id": context.agent_id,
        }
        try:
            query, requested_agent_id, limit = parse_memory_search_arguments(tool_call.arguments)
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

        search_agent_id = requested_agent_id or context.agent_id
        rows = await self._memory.search(
            user_id=context.owner_id,
            project_id=context.project_id,
            query=query,
            agent_id=search_agent_id,
            limit=limit,
        )
        items = [_format_memory_item(row) for row in rows]
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"items": items, "count": len(items)},
            reason=None,
        )
