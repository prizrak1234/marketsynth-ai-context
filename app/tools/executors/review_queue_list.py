"""Read-only review_queue.list tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.review_queue_service import ReviewQueueService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import MARKETING_FORBIDDEN_ARGUMENT_KEYS
from app.tools.permissions import ToolExecutionMode
from app.tools.review_queue_tools import (
    REVIEW_QUEUE_LIST_DEFAULT_LIMIT,
    REVIEW_QUEUE_LIST_MAX_LIMIT,
    REVIEW_QUEUE_LIST_TOOL_NAME,
    format_review_queue_list_compact,
)


@dataclass(frozen=True)
class ReviewQueueListOptions:
    limit: int = REVIEW_QUEUE_LIST_DEFAULT_LIMIT


def _coerce_limit(value: object) -> int:
    if value is None:
        return REVIEW_QUEUE_LIST_DEFAULT_LIMIT
    if not isinstance(value, int):
        raise ToolValidationError(
            "review_queue.list limit must be an integer",
            tool_name=REVIEW_QUEUE_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    if value < 1 or value > REVIEW_QUEUE_LIST_MAX_LIMIT:
        raise ToolValidationError(
            f"review_queue.list limit must be between 1 and {REVIEW_QUEUE_LIST_MAX_LIMIT}",
            tool_name=REVIEW_QUEUE_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    return value


def parse_review_queue_list_arguments(arguments: dict[str, Any]) -> ReviewQueueListOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"review_queue.list does not accept argument: {forbidden_key}",
                tool_name=REVIEW_QUEUE_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    return ReviewQueueListOptions(limit=_coerce_limit(arguments.get("limit")))


class ReviewQueueListToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._queue = ReviewQueueService(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": REVIEW_QUEUE_LIST_TOOL_NAME,
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
            options = parse_review_queue_list_arguments(tool_call.arguments)
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

        result = await self._queue.list_for_tool(
            context.owner_id,
            context.project_id,
            limit=options.limit,
        )
        if result is None:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="project_not_found",
                error_payload={
                    "error_type": "ProjectNotFound",
                    "safe_message": "Project not found",
                    "reason": "project_not_found",
                },
            )

        items, total_count = result
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=format_review_queue_list_compact(items, count=total_count),
            reason=None,
        )
