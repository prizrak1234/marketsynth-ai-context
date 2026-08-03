"""Read-only marketing_funnel.gap_analysis tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.funnel_step_asset_links import FunnelStepAssetLinkRepository
from app.db.repositories.marketing_funnel_steps import MarketingFunnelStepRepository
from app.db.repositories.marketing_funnels import MarketingFunnelRepository
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.funnel_tools import (
    FUNNEL_FORBIDDEN_ARGUMENT_KEYS,
    MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
    compute_funnel_gap_analysis,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class MarketingFunnelGapAnalysisOptions:
    funnel_id: UUID


def parse_marketing_funnel_gap_analysis_arguments(
    arguments: dict[str, Any],
) -> MarketingFunnelGapAnalysisOptions:
    for forbidden_key in FUNNEL_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                "marketing_funnel.gap_analysis does not accept argument: "
                f"{forbidden_key}",
                tool_name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    raw_funnel_id = arguments.get("funnel_id")
    if not isinstance(raw_funnel_id, str) or not raw_funnel_id.strip():
        raise ToolValidationError(
            "marketing_funnel.gap_analysis requires a non-empty funnel_id string",
            tool_name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        funnel_id = UUID(raw_funnel_id.strip())
    except ValueError as exc:
        raise ToolValidationError(
            "marketing_funnel.gap_analysis funnel_id must be a valid UUID",
            tool_name=MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc

    return MarketingFunnelGapAnalysisOptions(funnel_id=funnel_id)


class MarketingFunnelGapAnalysisToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._funnels = MarketingFunnelRepository(session)
        self._steps = MarketingFunnelStepRepository(session)
        self._links = FunnelStepAssetLinkRepository(session)
        self._assets = ContentAssetRepository(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME,
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
            options = parse_marketing_funnel_gap_analysis_arguments(tool_call.arguments)
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

        row = await self._funnels.get_by_id_for_project(
            options.funnel_id,
            context.owner_id,
            context.project_id,
        )
        if row is None:
            existing = await self._funnels.get_by_id(options.funnel_id)
            if existing is None:
                return ToolExecutionResult(
                    **base,
                    status=ToolExecutionStatus.FAILED,
                    reason="funnel_not_found",
                    error_payload={
                        "error_type": "FunnelNotFound",
                        "safe_message": "Marketing funnel not found",
                        "reason": "funnel_not_found",
                    },
                )
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="funnel_access_denied",
                error_payload={
                    "error_type": "FunnelAccessDenied",
                    "safe_message": "Marketing funnel access denied",
                    "reason": "funnel_access_denied",
                },
            )

        steps = await self._steps.list_by_funnel(
            row.id,
            context.owner_id,
            context.project_id,
            include_archived=True,
        )
        links = await self._links.list_by_funnel(
            row.id,
            context.owner_id,
            context.project_id,
        )

        asset_ids = {link.asset_id for link in links}
        linked_assets_by_id: dict[object, object] = {}
        for asset_id in asset_ids:
            asset = await self._assets.get_by_id_for_owner(
                asset_id,
                context.owner_id,
                context.project_id,
            )
            if asset is not None:
                linked_assets_by_id[asset_id] = asset

        analysis = compute_funnel_gap_analysis(
            steps=steps,
            links=links,
            linked_assets_by_id=linked_assets_by_id,
        )
        analysis["funnel_id"] = str(row.id)

        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=analysis,
            reason=None,
        )
