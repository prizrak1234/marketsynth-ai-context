"""Read-only marketing_brief.get tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.marketing_briefs import MarketingBriefRepository
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    MARKETING_BRIEF_GET_TOOL_NAME,
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
    format_marketing_brief_full,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingBriefGetOptions:
    brief_id: UUID
    include_constraints: bool = True


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"marketing_brief.get {field_name} must be a boolean",
        tool_name=MARKETING_BRIEF_GET_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def parse_marketing_brief_get_arguments(arguments: dict[str, Any]) -> MarketingBriefGetOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"marketing_brief.get does not accept argument: {forbidden_key}",
                tool_name=MARKETING_BRIEF_GET_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_brief_id = arguments.get("brief_id")
    if not isinstance(raw_brief_id, str) or not raw_brief_id.strip():
        raise ToolValidationError(
            "marketing_brief.get requires a non-empty brief_id string",
            tool_name=MARKETING_BRIEF_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        brief_id = UUID(raw_brief_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "marketing_brief.get brief_id must be a valid UUID",
            tool_name=MARKETING_BRIEF_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return MarketingBriefGetOptions(
        brief_id=brief_id,
        include_constraints=_coerce_bool(
            arguments.get("include_constraints"),
            field_name="include_constraints",
            default=True,
        ),
    )


class MarketingBriefGetToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._briefs = MarketingBriefRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_BRIEF_GET_TOOL_NAME,
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
            options = parse_marketing_brief_get_arguments(tool_call.arguments)
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

        row = await self._briefs.get_by_id_for_owner(
            options.brief_id,
            context.owner_id,
            context.project_id,
        )
        if row is None:
            existing = await self._briefs.get_by_id(options.brief_id)
            if existing is None:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="brief_not_found",
                    error_payload={
                        "error_type": "BriefNotFound",
                        "safe_message": "Marketing brief not found",
                        "reason": "brief_not_found",
                    },
                )
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="brief_access_denied",
                error_payload={
                    "error_type": "BriefAccessDenied",
                    "safe_message": "Marketing brief access denied",
                    "reason": "brief_access_denied",
                },
            )

        brief_payload = format_marketing_brief_full(
            row,
            include_constraints=options.include_constraints,
        )
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"brief": brief_payload, "count": 1},
            reason=None,
        )
