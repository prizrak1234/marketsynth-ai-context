"""Write tool: content_asset.create_draft (Phase 4.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sanitize_text
from app.db.repositories.marketing_briefs import MarketingBriefRepository
from app.marketing.content_plan_quality import (
    enrich_content_plan_metadata,
    is_content_plan_candidate,
)
from app.marketing.contracts import (
    ContentAssetStatus,
    ContentAssetType,
    ContentAssetVersionSource,
    MarketingBriefStatus,
)
from app.marketing.copy_quality import (
    enrich_copy_draft_metadata,
    is_copy_draft_candidate,
)
from app.marketing.research_quality import (
    enrich_research_draft_metadata,
    is_research_draft_candidate,
)
from app.marketing.review_quality import (
    enrich_content_review_metadata,
    is_content_review_candidate,
)
from app.marketing.strategy_contracts import (
    enrich_strategy_draft_metadata,
    is_strategy_draft_candidate,
)
from app.services.content_asset_service import ContentAssetService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CREATE_DRAFT_FORBIDDEN_ARGUMENT_KEYS,
    format_content_asset_create_draft_result,
    parse_content_asset_type,
    sanitize_create_draft_metadata,
)
from app.tools.permissions import ToolExecutionMode
from app.tools.write_tool_settings import get_agent_write_tool_body_max_chars


@dataclass(frozen=True)
class ContentAssetCreateDraftOptions:
    asset_type: ContentAssetType
    title: str
    body: str
    brief_id: UUID | None = None
    metadata: dict[str, Any] | None = None


def _require_non_empty_string(
    value: object,
    *,
    field_name: str,
    tool_name: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            f"{tool_name} requires a non-empty {field_name}",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    return value.strip()


def _coerce_brief_id(value: object, *, tool_name: str) -> UUID | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            f"{tool_name} brief_id must be a non-empty string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise ToolValidationError(
            f"{tool_name} brief_id must be a valid UUID",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        ) from exc


def parse_content_asset_create_draft_arguments(
    arguments: dict[str, Any],
) -> ContentAssetCreateDraftOptions:
    for forbidden_key in CREATE_DRAFT_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"{CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME} does not accept argument: {forbidden_key}",
                tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    title = _require_non_empty_string(
        arguments.get("title"),
        field_name="title",
        tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    )
    if len(title) > 200:
        raise ToolValidationError(
            "content_asset.create_draft title must be at most 200 characters",
            tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )

    body = _require_non_empty_string(
        arguments.get("body"),
        field_name="body",
        tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    )
    max_body = get_agent_write_tool_body_max_chars()
    if len(body) > max_body:
        raise ToolValidationError(
            f"content_asset.create_draft body exceeds maximum length ({max_body})",
            tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )

    asset_type = parse_content_asset_type(
        arguments.get("type"),
        tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    )
    assert asset_type is not None

    return ContentAssetCreateDraftOptions(
        asset_type=asset_type,
        title=title,
        body=sanitize_text(body),
        brief_id=_coerce_brief_id(
            arguments.get("brief_id"),
            tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
        ),
        metadata=sanitize_create_draft_metadata(
            arguments.get("metadata"),
            tool_name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
        ),
    )


class ContentAssetCreateDraftToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._assets = ContentAssetService(session)
        self._briefs = MarketingBriefRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        tool_name = CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
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
            options = parse_content_asset_create_draft_arguments(tool_call.arguments)
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

        if options.brief_id is not None:
            brief = await self._briefs.get_by_id_for_owner(
                options.brief_id,
                context.owner_id,
                context.project_id,
            )
            if brief is None:
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
            if brief.status == MarketingBriefStatus.ARCHIVED:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="invalid_tool_arguments",
                    error_payload={
                        "error_type": "InvalidToolArguments",
                        "safe_message": "Cannot create draft for an archived brief",
                        "reason": "invalid_tool_arguments",
                    },
                )

        asset_metadata = options.metadata
        if is_copy_draft_candidate(asset_metadata):
            asset_metadata = enrich_copy_draft_metadata(
                asset_metadata,
                asset_type=options.asset_type,
                body=options.body,
            )
        elif is_content_plan_candidate(asset_metadata):
            asset_metadata = enrich_content_plan_metadata(asset_metadata, options.body)
        elif is_content_review_candidate(asset_metadata):
            asset_metadata = enrich_content_review_metadata(asset_metadata, options.body)
        elif is_research_draft_candidate(asset_metadata):
            asset_metadata = enrich_research_draft_metadata(asset_metadata, options.body)
        elif is_strategy_draft_candidate(
            options.asset_type,
            options.title,
            asset_metadata,
        ):
            asset_metadata = enrich_strategy_draft_metadata(asset_metadata, options.body)

        row = await self._assets.create(
            context.owner_id,
            context.project_id,
            asset_type=options.asset_type,
            title=options.title,
            body=options.body,
            metadata=asset_metadata,
            status=ContentAssetStatus.DRAFT,
            brief_id=options.brief_id,
            task_id=context.task_id,
            agent_run_id=context.agent_run_id,
            created_by_source=ContentAssetVersionSource.AGENT_TOOL,
            created_by_agent_run_id=context.agent_run_id,
        )
        if row is None:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="asset_create_failed",
                error_payload={
                    "error_type": "AssetCreateFailed",
                    "safe_message": "Failed to create content asset",
                    "reason": "asset_create_failed",
                },
            )

        asset_payload = format_content_asset_create_draft_result(row)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"asset": asset_payload, "count": 1},
            reason=None,
        )
