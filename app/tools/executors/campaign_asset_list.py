"""Read-only campaign_asset.list tool executor — assets scoped to one campaign."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.marketing.contracts import ContentAssetStatus, ContentAssetType
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.content_asset_list import (
    _coerce_bool,
    _coerce_limit,
)
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
    coerce_required_uuid_argument,
    format_content_asset_compact,
    parse_content_asset_status,
    parse_content_asset_type,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class CampaignAssetListOptions:
    campaign_id: UUID
    limit: int
    asset_type: ContentAssetType | None = None
    status: ContentAssetStatus | None = None
    include_archived: bool = False


def parse_campaign_asset_list_arguments(arguments: dict[str, Any]) -> CampaignAssetListOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"campaign_asset.list does not accept argument: {forbidden_key}",
                tool_name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    return CampaignAssetListOptions(
        campaign_id=coerce_required_uuid_argument(
            arguments.get("campaign_id"),
            field_name="campaign_id",
            tool_name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
        ),
        limit=_coerce_limit(arguments.get("limit"), tool_name=CAMPAIGN_ASSET_LIST_TOOL_NAME),
        asset_type=parse_content_asset_type(
            arguments.get("type"),
            tool_name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
        ),
        status=parse_content_asset_status(
            arguments.get("status"),
            tool_name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
        ),
        include_archived=_coerce_bool(
            arguments.get("include_archived"),
            field_name="include_archived",
            default=False,
            tool_name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
        ),
    )


class CampaignAssetListToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._assets = ContentAssetRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": CAMPAIGN_ASSET_LIST_TOOL_NAME,
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
            options = parse_campaign_asset_list_arguments(tool_call.arguments)
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

        rows = await self._assets.list_by_campaign(
            context.owner_id,
            context.project_id,
            options.campaign_id,
            include_archived=options.include_archived,
            status=options.status,
            asset_type=options.asset_type,
            limit=options.limit,
        )
        items = [format_content_asset_compact(row) for row in rows]
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={
                "items": items,
                "count": len(items),
                "campaign_id": str(options.campaign_id),
            },
            reason=None,
        )
