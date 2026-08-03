"""Read-only content_asset.get tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.tools.asset_read_settings import is_agent_allowed_content_asset_get_body
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    CONTENT_ASSET_GET_TOOL_NAME,
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
    format_content_asset_full,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class ContentAssetGetOptions:
    asset_id: UUID
    include_body: bool = False


def _coerce_bool(value: object, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ToolValidationError(
        f"content_asset.get {field_name} must be a boolean",
        tool_name=CONTENT_ASSET_GET_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def parse_content_asset_get_arguments(arguments: dict[str, Any]) -> ContentAssetGetOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"content_asset.get does not accept argument: {forbidden_key}",
                tool_name=CONTENT_ASSET_GET_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_asset_id = arguments.get("asset_id")
    if not isinstance(raw_asset_id, str) or not raw_asset_id.strip():
        raise ToolValidationError(
            "content_asset.get requires a non-empty asset_id string",
            tool_name=CONTENT_ASSET_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        asset_id = UUID(raw_asset_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "content_asset.get asset_id must be a valid UUID",
            tool_name=CONTENT_ASSET_GET_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return ContentAssetGetOptions(
        asset_id=asset_id,
        include_body=_coerce_bool(
            arguments.get("include_body"),
            field_name="include_body",
            default=False,
        ),
    )


class ContentAssetGetToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._assets = ContentAssetRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": CONTENT_ASSET_GET_TOOL_NAME,
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
            options = parse_content_asset_get_arguments(tool_call.arguments)
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

        if options.include_body and not is_agent_allowed_content_asset_get_body(
            context.agent_type,
        ):
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="agent_type_not_allowed",
                error_payload={
                    "error_type": "AgentTypeNotAllowed",
                    "safe_message": "Content asset body is not available for this agent type",
                    "reason": "agent_type_not_allowed",
                },
            )

        row = await self._assets.get_by_id_for_owner(
            options.asset_id,
            context.owner_id,
            context.project_id,
        )
        if row is None:
            existing = await self._assets.get_by_id(options.asset_id)
            if existing is None:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="asset_not_found",
                    error_payload={
                        "error_type": "AssetNotFound",
                        "safe_message": "Content asset not found",
                        "reason": "asset_not_found",
                    },
                )
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="asset_access_denied",
                error_payload={
                    "error_type": "AssetAccessDenied",
                    "safe_message": "Content asset access denied",
                    "reason": "asset_access_denied",
                },
            )

        asset_payload = format_content_asset_full(row, include_body=options.include_body)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"asset": asset_payload, "count": 1},
            reason=None,
        )
