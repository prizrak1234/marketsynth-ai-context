"""Read-only marketing_funnel.list tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.marketing_funnel_steps import MarketingFunnelStepRepository
from app.db.repositories.marketing_funnels import MarketingFunnelRepository
from app.marketing.funnel_contracts import MarketingFunnelStatus
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.funnel_tools import (
    FUNNEL_FORBIDDEN_ARGUMENT_KEYS,
    MARKETING_FUNNEL_LIST_DEFAULT_LIMIT,
    MARKETING_FUNNEL_LIST_MAX_LIMIT,
    MARKETING_FUNNEL_LIST_TOOL_NAME,
    format_funnel_list_item,
    parse_marketing_funnel_status,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingFunnelListOptions:
    limit: int = MARKETING_FUNNEL_LIST_DEFAULT_LIMIT
    status: MarketingFunnelStatus | None = None
    include_archived: bool = False


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"marketing_funnel.list {field_name} must be a boolean",
        tool_name=MARKETING_FUNNEL_LIST_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def _coerce_limit(value: object) -> int:
    if value is None:
        return MARKETING_FUNNEL_LIST_DEFAULT_LIMIT
    if not isinstance(value, int):
        raise ToolValidationError(
            "marketing_funnel.list limit must be an integer",
            tool_name=MARKETING_FUNNEL_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    if value < 1:
        raise ToolValidationError(
            "marketing_funnel.list limit must be at least 1",
            tool_name=MARKETING_FUNNEL_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    return min(value, MARKETING_FUNNEL_LIST_MAX_LIMIT)


def parse_marketing_funnel_list_arguments(arguments: dict[str, Any]) -> MarketingFunnelListOptions:
    for forbidden_key in FUNNEL_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"marketing_funnel.list does not accept argument: {forbidden_key}",
                tool_name=MARKETING_FUNNEL_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    return MarketingFunnelListOptions(
        limit=_coerce_limit(arguments.get("limit")),
        status=parse_marketing_funnel_status(
            arguments.get("status"),
            tool_name=MARKETING_FUNNEL_LIST_TOOL_NAME,
        ),
        include_archived=_coerce_bool(
            arguments.get("include_archived"),
            field_name="include_archived",
            default=False,
        ),
    )


class MarketingFunnelListToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._funnels = MarketingFunnelRepository(session)
        self._steps = MarketingFunnelStepRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_FUNNEL_LIST_TOOL_NAME,
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
            options = parse_marketing_funnel_list_arguments(tool_call.arguments)
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

        rows = await self._funnels.list_by_project(
            context.owner_id,
            context.project_id,
            include_archived=options.include_archived,
            status=options.status,
            limit=options.limit,
        )

        items: list[dict[str, Any]] = []
        for row in rows:
            step_rows = await self._steps.list_by_funnel(
                row.id,
                context.owner_id,
                context.project_id,
                include_archived=False,
            )
            items.append(format_funnel_list_item(row, steps_count=len(step_rows)))

        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"items": items, "count": len(items)},
            reason=None,
        )
