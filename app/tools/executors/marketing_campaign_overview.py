"""Read-only marketing_campaign.overview tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.campaign_overview_service import CampaignOverviewService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingCampaignOverviewOptions:
    campaign_id: UUID


def parse_marketing_campaign_overview_arguments(
    arguments: dict[str, Any],
) -> MarketingCampaignOverviewOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"marketing_campaign.overview does not accept argument: {forbidden_key}",
                tool_name=MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_campaign_id = arguments.get("campaign_id")
    if not isinstance(raw_campaign_id, str) or not raw_campaign_id.strip():
        raise ToolValidationError(
            "marketing_campaign.overview requires a non-empty campaign_id string",
            tool_name=MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        campaign_id = UUID(raw_campaign_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "marketing_campaign.overview campaign_id must be a valid UUID",
            tool_name=MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return MarketingCampaignOverviewOptions(campaign_id=campaign_id)


class MarketingCampaignOverviewToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._overview = CampaignOverviewService(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME,
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
            options = parse_marketing_campaign_overview_arguments(tool_call.arguments)
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

        overview = await self._overview.get_overview(
            owner_id=context.owner_id,
            project_id=context.project_id,
            campaign_id=options.campaign_id,
        )
        if overview is None:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="campaign_not_found",
                error_payload={
                    "error_type": "CampaignNotFound",
                    "safe_message": "Marketing campaign not found",
                    "reason": "campaign_not_found",
                },
            )

        payload = overview.model_dump(mode="json", exclude_none=True)
        # Tools must never include campaign_metadata (avoid inflating context).
        campaign = payload.get("campaign")
        if isinstance(campaign, dict):
            campaign.pop("campaign_metadata", None)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=payload,
            reason=None,
        )

