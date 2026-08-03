"""Read-only marketing_funnel.step_assets tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.funnel_step_asset_links import FunnelStepAssetLinkRepository
from app.db.repositories.marketing_funnel_steps import MarketingFunnelStepRepository
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.funnel_tools import (
    FUNNEL_FORBIDDEN_ARGUMENT_KEYS,
    MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
    format_funnel_step_asset_item,
    format_funnel_step_assets_step,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingFunnelStepAssetsOptions:
    step_id: UUID


def parse_marketing_funnel_step_assets_arguments(
    arguments: dict[str, Any],
) -> MarketingFunnelStepAssetsOptions:
    for forbidden_key in FUNNEL_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                "marketing_funnel.step_assets does not accept argument: "
                f"{forbidden_key}",
                tool_name=MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_step_id = arguments.get("step_id")
    if not isinstance(raw_step_id, str) or not raw_step_id.strip():
        raise ToolValidationError(
            "marketing_funnel.step_assets requires a non-empty step_id string",
            tool_name=MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        step_id = UUID(raw_step_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "marketing_funnel.step_assets step_id must be a valid UUID",
            tool_name=MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return MarketingFunnelStepAssetsOptions(step_id=step_id)


class MarketingFunnelStepAssetsToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._steps = MarketingFunnelStepRepository(session)
        self._links = FunnelStepAssetLinkRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME,
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
            options = parse_marketing_funnel_step_assets_arguments(tool_call.arguments)
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

        step = await self._steps.get_by_id_for_project(
            options.step_id,
            context.owner_id,
            context.project_id,
        )
        if step is None:
            existing = await self._steps.get_by_id(options.step_id)
            if existing is None:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="step_not_found",
                    error_payload={
                        "error_type": "FunnelStepNotFound",
                        "safe_message": "Funnel step not found",
                        "reason": "step_not_found",
                    },
                )
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="step_access_denied",
                error_payload={
                    "error_type": "FunnelStepAccessDenied",
                    "safe_message": "Funnel step access denied",
                    "reason": "step_access_denied",
                },
            )

        link_rows = await self._links.list_by_step(
            step.id,
            step.funnel_id,
            context.owner_id,
            context.project_id,
        )
        assets = [format_funnel_step_asset_item(link) for link in link_rows]

        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={
                "step": format_funnel_step_assets_step(step),
                "assets": assets,
                "count": len(assets),
            },
            reason=None,
        )
