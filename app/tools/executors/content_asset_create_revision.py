"""Write tool: content_asset.create_revision (Phase 12.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.repositories.content_assets import ContentAssetRepository
from app.services.content_asset_service import ContentAssetService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
    CREATE_REVISION_FORBIDDEN_ARGUMENT_KEYS,
    format_content_asset_create_revision_result,
    reject_secrets_in_revision_body,
    validate_revision_metadata_patch,
)
from app.tools.permissions import ToolExecutionMode
from app.tools.write_tool_settings import get_agent_write_tool_body_max_chars


@dataclass(frozen=True)
class ContentAssetCreateRevisionOptions:
    project_id: UUID
    asset_id: UUID
    body: str
    title: str | None = None
    metadata_patch: dict[str, Any] | None = None


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


def parse_content_asset_create_revision_arguments(
    arguments: dict[str, Any],
) -> ContentAssetCreateRevisionOptions:
    tool_name = CONTENT_ASSET_CREATE_REVISION_TOOL_NAME
    for forbidden_key in CREATE_REVISION_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"{tool_name} does not accept argument: {forbidden_key}",
                tool_name=tool_name,
                original_error_type="InvalidToolArguments",
            )

    body_raw = arguments.get("body")
    if not isinstance(body_raw, str) or not body_raw.strip():
        raise ToolValidationError(
            f"{tool_name} requires a non-empty body string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    body = sanitize_text(body_raw.strip())
    reject_secrets_in_revision_body(body, tool_name=tool_name)

    max_body = get_agent_write_tool_body_max_chars()
    if len(body) > max_body:
        raise ToolValidationError(
            f"{tool_name} body exceeds maximum length ({max_body})",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    title: str | None = None
    if "title" in arguments and arguments["title"] is not None:
        title_raw = arguments["title"]
        if not isinstance(title_raw, str) or not title_raw.strip():
            raise ToolValidationError(
                f"{tool_name} title must be a non-empty string when provided",
                tool_name=tool_name,
                original_error_type="InvalidToolArguments",
            )
        title = sanitize_text(title_raw.strip())
        if len(title) > 200:
            raise ToolValidationError(
                f"{tool_name} title must be at most 200 characters",
                tool_name=tool_name,
                original_error_type="InvalidToolArguments",
            )

    return ContentAssetCreateRevisionOptions(
        project_id=_parse_uuid(
            arguments.get("project_id"),
            field_name="project_id",
            tool_name=tool_name,
        ),
        asset_id=_parse_uuid(
            arguments.get("asset_id"),
            field_name="asset_id",
            tool_name=tool_name,
        ),
        body=body,
        title=title,
        metadata_patch=validate_revision_metadata_patch(
            arguments.get("metadata_patch"),
            tool_name=tool_name,
        ),
    )


class ContentAssetCreateRevisionToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._assets = ContentAssetService(session)
        self._repo = ContentAssetRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        tool_name = CONTENT_ASSET_CREATE_REVISION_TOOL_NAME
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
            options = parse_content_asset_create_revision_arguments(tool_call.arguments)
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

        if options.project_id != context.project_id:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="project_access_denied",
                error_payload={
                    "error_type": "ProjectAccessDenied",
                    "safe_message": "Project access denied",
                    "reason": "project_access_denied",
                },
            )

        try:
            row = await self._assets.apply_agent_content_revision(
                context.owner_id,
                context.project_id,
                options.asset_id,
                body=options.body,
                title=options.title,
                metadata_patch=options.metadata_patch,
                created_by_agent_run_id=context.agent_run_id,
            )
        except InvalidStateError as exc:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="invalid_asset_state",
                error_payload={
                    "error_type": "InvalidState",
                    "safe_message": str(exc),
                    "reason": "invalid_asset_state",
                },
            )

        if row is None:
            existing = await self._repo.get_by_id(options.asset_id)
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

        payload = format_content_asset_create_revision_result(row)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=payload,
            reason=None,
        )
