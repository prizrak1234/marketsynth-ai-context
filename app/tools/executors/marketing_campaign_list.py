"""Read-only marketing_campaign.list tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.marketing_campaigns import MarketingCampaignRepository
from app.marketing.contracts import MarketingCampaignStatus
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    MARKETING_CAMPAIGN_LIST_DEFAULT_LIMIT,
    MARKETING_CAMPAIGN_LIST_MAX_LIMIT,
    MARKETING_CAMPAIGN_LIST_TOOL_NAME,
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
    format_marketing_campaign_safe,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingCampaignListOptions:
    status: MarketingCampaignStatus | None = None
    limit: int = MARKETING_CAMPAIGN_LIST_DEFAULT_LIMIT
    include_archived: bool = False


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"marketing_campaign.list {field_name} must be a boolean",
        tool_name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def _coerce_int(value: object, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    raise ToolValidationError(
        f"marketing_campaign.list {field_name} must be an integer",
        tool_name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def parse_marketing_campaign_list_arguments(
    arguments: dict[str, Any],
) -> MarketingCampaignListOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"marketing_campaign.list does not accept argument: {forbidden_key}",
                tool_name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    status: MarketingCampaignStatus | None = None
    raw_status = arguments.get("status")
    if raw_status is not None:
        if not isinstance(raw_status, str) or not raw_status.strip():
            raise ToolValidationError(
                "marketing_campaign.list status must be a non-empty string",
                tool_name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )
        try:
            status = MarketingCampaignStatus(raw_status.strip())
        except ValueError as exc:
            raise ToolValidationError(
                "marketing_campaign.list status is invalid",
                tool_name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            ) from exc

    limit = _coerce_int(
        arguments.get("limit"),
        field_name="limit",
        default=MARKETING_CAMPAIGN_LIST_DEFAULT_LIMIT,
    )
    if limit < 1 or limit > MARKETING_CAMPAIGN_LIST_MAX_LIMIT:
        raise ToolValidationError(
            (
                "marketing_campaign.list limit must be between 1 and "
                f"{MARKETING_CAMPAIGN_LIST_MAX_LIMIT}"
            ),
            tool_name=MARKETING_CAMPAIGN_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )

    include_archived = _coerce_bool(
        arguments.get("include_archived"),
        field_name="include_archived",
        default=False,
    )

    return MarketingCampaignListOptions(
        status=status,
        limit=limit,
        include_archived=include_archived,
    )


class MarketingCampaignListToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._campaigns = MarketingCampaignRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_CAMPAIGN_LIST_TOOL_NAME,
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
            options = parse_marketing_campaign_list_arguments(tool_call.arguments)
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

        rows = await self._campaigns.list_for_project(
            context.owner_id,
            context.project_id,
            status=options.status,
            include_archived=options.include_archived,
            limit=options.limit,
            offset=0,
        )
        items = [format_marketing_campaign_safe(row) for row in rows]
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"items": items, "count": len(items)},
            reason=None,
        )

