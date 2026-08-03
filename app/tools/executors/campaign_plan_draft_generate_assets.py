"""Write tool: campaign_plan_draft.generate_assets (Phase AI.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.marketing.plan_draft_asset_mapping import PLAN_DRAFT_GENERATION_PARTIAL_STATE
from app.services.campaign_plan_draft_service import CampaignPlanDraftService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_FORBIDDEN_ARGUMENT_KEYS,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    format_campaign_plan_draft_generate_assets_result,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class CampaignPlanDraftGenerateAssetsOptions:
    campaign_id: UUID
    draft_id: UUID


def _parse_uuid(value: object, *, field_name: str, tool_name: str) -> UUID:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            f"{tool_name} requires a non-empty {field_name} string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise ToolValidationError(
            f"{tool_name} {field_name} must be a valid UUID",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        ) from exc


def parse_campaign_plan_draft_generate_assets_arguments(
    arguments: dict[str, Any],
) -> CampaignPlanDraftGenerateAssetsOptions:
    tool_name = CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME
    forbidden_keys = CAMPAIGN_PLAN_DRAFT_FORBIDDEN_ARGUMENT_KEYS | frozenset({"project_id"})
    for forbidden_key in forbidden_keys:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"{tool_name} does not accept argument: {forbidden_key}",
                tool_name=tool_name,
                original_error_type="InvalidToolArguments",
            )

    return CampaignPlanDraftGenerateAssetsOptions(
        campaign_id=_parse_uuid(
            arguments.get("campaign_id"),
            field_name="campaign_id",
            tool_name=tool_name,
        ),
        draft_id=_parse_uuid(
            arguments.get("draft_id"),
            field_name="draft_id",
            tool_name=tool_name,
        ),
    )


def _map_invalid_state_reason(message: str) -> str:
    lowered = message.lower()
    if "archived campaign" in lowered:
        return "campaign_archived"
    if "archived plan draft" in lowered:
        return "plan_draft_archived"
    if message == PLAN_DRAFT_GENERATION_PARTIAL_STATE:
        return "plan_draft_generation_partial_state"
    if "no content_items" in lowered or "content_items exceeds" in lowered:
        return "invalid_plan_payload"
    return "invalid_state"


class CampaignPlanDraftGenerateAssetsToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._drafts = CampaignPlanDraftService(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        tool_name = CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME
        base = {
            "tool_name": tool_name,
            "execution_mode": ToolExecutionMode.WRITE,
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
            options = parse_campaign_plan_draft_generate_assets_arguments(tool_call.arguments)
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

        try:
            result = await self._drafts.generate_assets(
                context.owner_id,
                context.project_id,
                options.campaign_id,
                options.draft_id,
            )
        except InvalidStateError as exc:
            reason = _map_invalid_state_reason(str(exc))
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason=reason,
                error_payload={
                    "error_type": "InvalidState",
                    "safe_message": str(exc),
                    "reason": reason,
                },
            )

        if result is None:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="campaign_not_found",
                error_payload={
                    "error_type": "CampaignNotFound",
                    "safe_message": "Campaign or plan draft not found",
                    "reason": "campaign_not_found",
                },
            )

        payload = format_campaign_plan_draft_generate_assets_result(result)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=payload,
            reason=None,
        )
