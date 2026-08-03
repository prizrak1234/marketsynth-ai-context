"""Read-only marketing_funnel.get tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.marketing_funnel_steps import MarketingFunnelStepRepository
from app.db.repositories.marketing_funnels import MarketingFunnelRepository
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.funnel_tools import (
    FUNNEL_FORBIDDEN_ARGUMENT_KEYS,
    MARKETING_FUNNEL_GET_TOOL_NAME,
    format_funnel_get_payload,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingFunnelGetOptions:
    funnel_id: UUID
    include_steps: bool = True


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"marketing_funnel.get {field_name} must be a boolean",
        tool_name=MARKETING_FUNNEL_GET_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def parse_marketing_funnel_get_arguments(arguments: dict[str, Any]) -> MarketingFunnelGetOptions:
    for forbidden_key in FUNNEL_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"marketing_funnel.get does not accept argument: {forbidden_key}",
                tool_name=MARKETING_FUNNEL_GET_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_funnel_id = arguments.get("funnel_id")
    if not isinstance(raw_funnel_id, str) or not raw_funnel_id.strip():
        raise ToolValidationError(
            "marketing_funnel.get requires a non-empty funnel_id string",
            tool_name=MARKETING_FUNNEL_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        funnel_id = UUID(raw_funnel_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "marketing_funnel.get funnel_id must be a valid UUID",
            tool_name=MARKETING_FUNNEL_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return MarketingFunnelGetOptions(
        funnel_id=funnel_id,
        include_steps=_coerce_bool(
            arguments.get("include_steps"),
            field_name="include_steps",
            default=True,
        ),
    )


class MarketingFunnelGetToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._funnels = MarketingFunnelRepository(session)
        self._steps = MarketingFunnelStepRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_FUNNEL_GET_TOOL_NAME,
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
            options = parse_marketing_funnel_get_arguments(tool_call.arguments)
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

        row = await self._funnels.get_by_id_for_project(
            options.funnel_id,
            context.owner_id,
            context.project_id,
        )
        if row is None:
            existing = await self._funnels.get_by_id(options.funnel_id)
            if existing is None:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="funnel_not_found",
                    error_payload={
                        "error_type": "FunnelNotFound",
                        "safe_message": "Marketing funnel not found",
                        "reason": "funnel_not_found",
                    },
                )
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="funnel_access_denied",
                error_payload={
                    "error_type": "FunnelAccessDenied",
                    "safe_message": "Marketing funnel access denied",
                    "reason": "funnel_access_denied",
                },
            )

        active_steps = await self._steps.list_by_funnel(
            row.id,
            context.owner_id,
            context.project_id,
            include_archived=False,
        )
        if options.include_steps:
            funnel_payload = format_funnel_get_payload(row, steps=active_steps)
        else:
            funnel_payload = format_funnel_get_payload(row, steps=None)
            funnel_payload["steps_count"] = len(active_steps)

        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"funnel": funnel_payload, "count": 1},
            reason=None,
        )
