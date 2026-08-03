"""Read-only content_asset.list tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.marketing.contracts import ContentAssetStatus, ContentAssetType
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    CONTENT_ASSET_LIST_DEFAULT_LIMIT,
    CONTENT_ASSET_LIST_MAX_LIMIT,
    CONTENT_ASSET_LIST_TOOL_NAME,
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
    coerce_optional_uuid_argument,
    format_content_asset_compact,
    parse_content_asset_status,
    parse_content_asset_type,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class ContentAssetListOptions:
    limit: int = CONTENT_ASSET_LIST_DEFAULT_LIMIT
    brief_id: UUID | None = None
    campaign_id: UUID | None = None
    asset_type: ContentAssetType | None = None
    status: ContentAssetStatus | None = None
    include_archived: bool = False


def _coerce_bool(
    value: object,
    *,
    field_name: str,
    default: bool,
    tool_name: str = CONTENT_ASSET_LIST_TOOL_NAME,
) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"{tool_name} {field_name} must be a boolean",
        tool_name=tool_name,
        original_error_type="InvalidToolArguments",
    )


def _coerce_limit(
    value: object,
    *,
    tool_name: str = CONTENT_ASSET_LIST_TOOL_NAME,
) -> int:
    if value is None:
        return CONTENT_ASSET_LIST_DEFAULT_LIMIT
    if not isinstance(value, int):
        raise ToolValidationError(
            f"{tool_name} limit must be an integer",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    if value < 1:
        raise ToolValidationError(
            f"{tool_name} limit must be at least 1",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    return min(value, CONTENT_ASSET_LIST_MAX_LIMIT)


def parse_content_asset_list_arguments(arguments: dict[str, Any]) -> ContentAssetListOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"content_asset.list does not accept argument: {forbidden_key}",
                tool_name=CONTENT_ASSET_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    brief_id = coerce_optional_uuid_argument(
        arguments.get("brief_id"),
        field_name="brief_id",
        tool_name=CONTENT_ASSET_LIST_TOOL_NAME,
    )
    campaign_id = coerce_optional_uuid_argument(
        arguments.get("campaign_id"),
        field_name="campaign_id",
        tool_name=CONTENT_ASSET_LIST_TOOL_NAME,
    )
    if brief_id is not None and campaign_id is not None:
        raise ToolValidationError(
            "content_asset.list accepts brief_id or campaign_id, not both",
            tool_name=CONTENT_ASSET_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )

    return ContentAssetListOptions(
        limit=_coerce_limit(arguments.get("limit")),
        brief_id=brief_id,
        campaign_id=campaign_id,
        asset_type=parse_content_asset_type(
            arguments.get("type"),
            tool_name=CONTENT_ASSET_LIST_TOOL_NAME,
        ),
        status=parse_content_asset_status(
            arguments.get("status"),
            tool_name=CONTENT_ASSET_LIST_TOOL_NAME,
        ),
        include_archived=_coerce_bool(
            arguments.get("include_archived"),
            field_name="include_archived",
            default=False,
        ),
    )


class ContentAssetListToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._assets = ContentAssetRepository(session)

    async def _list_rows(
        self,
        context: ToolExecutionContext,
        options: ContentAssetListOptions,
    ) -> list[object]:
        common = {
            "include_archived": options.include_archived,
            "status": options.status,
            "asset_type": options.asset_type,
            "limit": options.limit,
        }
        if options.brief_id is not None:
            return await self._assets.list_by_brief(
                context.owner_id,
                context.project_id,
                options.brief_id,
                **common,
            )
        if options.campaign_id is not None:
            return await self._assets.list_by_campaign(
                context.owner_id,
                context.project_id,
                options.campaign_id,
                **common,
            )
        return await self._assets.list_by_project(
            context.owner_id,
            context.project_id,
            **common,
        )

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": CONTENT_ASSET_LIST_TOOL_NAME,
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
            options = parse_content_asset_list_arguments(tool_call.arguments)
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

        rows = await self._list_rows(context, options)
        items = [format_content_asset_compact(row) for row in rows]
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"items": items, "count": len(items)},
            reason=None,
        )
