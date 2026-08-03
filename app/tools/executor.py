"""Safe tool executor — no-op by default, explicit read-only execution for memory.search."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.services.memory_service import MemoryService
from app.tools.argument_validator import validate_tool_arguments
from app.tools.contracts import ToolCall, ToolExecutionContext, ToolResult
from app.tools.errors import normalize_tool_error
from app.tools.execution_contracts import ToolExecutionResult
from app.tools.executors.campaign_asset_list import CampaignAssetListToolExecutor
from app.tools.executors.campaign_plan_draft_create import CampaignPlanDraftCreateToolExecutor
from app.tools.executors.campaign_plan_draft_generate_assets import (
    CampaignPlanDraftGenerateAssetsToolExecutor,
)
from app.tools.executors.content_asset_create_draft import ContentAssetCreateDraftToolExecutor
from app.tools.executors.content_asset_create_revision import (
    ContentAssetCreateRevisionToolExecutor,
)
from app.tools.executors.content_asset_get import ContentAssetGetToolExecutor
from app.tools.executors.content_asset_list import ContentAssetListToolExecutor
from app.tools.executors.marketing_brief_get import MarketingBriefGetToolExecutor
from app.tools.executors.marketing_brief_list import MarketingBriefListToolExecutor
from app.tools.executors.marketing_campaign_get import MarketingCampaignGetToolExecutor
from app.tools.executors.marketing_campaign_list import MarketingCampaignListToolExecutor
from app.tools.executors.marketing_campaign_overview import MarketingCampaignOverviewToolExecutor
from app.tools.executors.marketing_campaign_workflow import (
    MarketingCampaignWorkflowToolExecutor,
)
from app.tools.executors.marketing_funnel_gap_analysis import (
    MarketingFunnelGapAnalysisToolExecutor,
)
from app.tools.executors.marketing_funnel_get import MarketingFunnelGetToolExecutor
from app.tools.executors.marketing_funnel_list import MarketingFunnelListToolExecutor
from app.tools.executors.marketing_funnel_step_assets import (
    MarketingFunnelStepAssetsToolExecutor,
)
from app.tools.executors.memory_search import MemorySearchToolExecutor
from app.tools.executors.project_context_get import ProjectContextGetToolExecutor
from app.tools.executors.publication_calendar_list import PublicationCalendarListToolExecutor
from app.tools.executors.review_queue_list import ReviewQueueListToolExecutor
from app.tools.executors.task_get import TaskGetToolExecutor
from app.tools.executors.task_list_recent import TaskListRecentToolExecutor
from app.tools.permissions import (
    ToolAccessDecision,
    ToolAccessReasonCode,
    ToolExecutionMode,
    evaluate_tool_access,
    is_real_read_only_executable,
)
from app.tools.registry import ToolRegistry, get_tool_registry
from app.tools.result_builder import build_tool_error, envelope_from_execution
from app.tools.result_contracts import ToolExecutionErrorCode, is_tool_result_envelope
from app.tools.security import sanitize_tool_result
from app.tools.write_tool_settings import is_real_write_executable

if TYPE_CHECKING:
    from app.services.tool_execution_log_service import ToolExecutionLogService

log = get_logger(__name__)


def build_tools_run_summary(tool_results: list[ToolResult]) -> dict[str, Any]:
    tool_names: list[str] = []
    seen: set[str] = set()
    for result in tool_results:
        if result.name not in seen:
            seen.add(result.name)
            tool_names.append(result.name)
    return {
        "executed_count": sum(1 for result in tool_results if result.status == "succeeded"),
        "failed_count": sum(1 for result in tool_results if result.status == "failed"),
        "tool_names": tool_names,
    }


def _tool_result_summary(result: ToolResult) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "call_id": result.call_id,
        "name": result.name,
        "status": result.status,
    }
    if isinstance(result.output, dict):
        if is_tool_result_envelope(result.output):
            if result.output.get("ok"):
                meta = result.output.get("meta") or {}
                if meta.get("items_count") is not None:
                    summary["items_count"] = meta["items_count"]
            else:
                error = result.output.get("error") or {}
                if error.get("code"):
                    summary["error_code"] = error["code"]
        reason = result.output.get("reason")
        if reason is not None:
            summary["reason"] = reason
    metadata_reason = result.metadata.get("reason")
    if metadata_reason is not None and "reason" not in summary:
        summary["reason"] = metadata_reason
    if result.error is not None:
        summary["error_type"] = result.error.get("error_type")
        summary["safe_message"] = result.error.get("safe_message")
    return summary


def _tool_execution_summary(result: ToolResult) -> dict[str, Any]:
    execution_mode = result.metadata.get("execution_mode", ToolExecutionMode.NO_OP.value)
    summary: dict[str, Any] = {
        "tool_name": result.name,
        "status": result.status,
        "execution_mode": execution_mode,
        "reason": result.metadata.get("reason"),
    }
    result_count = result.metadata.get("result_count")
    if result_count is not None:
        summary["result_count"] = result_count
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        error = result.output.get("error") or {}
        if error.get("code"):
            summary["error_code"] = error["code"]
    if result.error is not None:
        summary["error_type"] = result.error.get("error_type")
    if summary.get("reason") is None and isinstance(result.output, dict):
        summary["reason"] = result.output.get("reason")
    return summary


def build_tool_call_metadata(
    *,
    available_tool_names: list[str],
    tool_results: list[ToolResult],
    tool_choice: str | None = None,
    permission_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "tools_enabled": bool(available_tool_names),
        "tool_count": len(available_tool_names),
        "tool_names": available_tool_names,
        "tool_calls_detected": len(tool_results),
        "tool_calls_executed": sum(1 for result in tool_results if result.status == "succeeded"),
        "tool_calls_skipped": sum(1 for result in tool_results if result.status == "skipped"),
        "tool_results": [_tool_result_summary(result) for result in tool_results],
        "tool_executions": [_tool_execution_summary(result) for result in tool_results],
        "tool_choice": tool_choice,
    }
    if permission_policy is not None:
        metadata["permission_policy"] = permission_policy
    metadata["tools"] = build_tools_run_summary(tool_results)
    return metadata


def enrich_tool_round_metadata(
    metadata: dict[str, Any],
    *,
    tool_rounds: int,
    follow_up_llm_call: bool,
    nested_tool_calls: bool,
) -> dict[str, Any]:
    enriched = dict(metadata)
    enriched["tool_rounds"] = tool_rounds
    enriched["follow_up_llm_call"] = follow_up_llm_call
    enriched["nested_tool_calls"] = nested_tool_calls
    return enriched


def _tool_result_from_envelope(
    tool_call: ToolCall,
    envelope: dict[str, Any],
    *,
    execution_mode: str,
    reason: str | None = None,
) -> ToolResult:
    ok = bool(envelope.get("ok"))
    meta = envelope.get("meta") or {}
    metadata: dict[str, Any] = {
        "execution_mode": execution_mode,
        "reason": reason or (envelope.get("error") or {}).get("code"),
    }
    items_count = meta.get("items_count")
    if items_count is not None:
        metadata["result_count"] = items_count

    if ok:
        return ToolResult(
            call_id=tool_call.id,
            name=tool_call.name,
            status="succeeded",
            output=envelope,
            metadata=metadata,
        )

    error = envelope.get("error") or {}
    return ToolResult(
        call_id=tool_call.id,
        name=tool_call.name,
        status="failed",
        output=envelope,
        error={
            "error_type": error.get("code"),
            "safe_message": error.get("message"),
            "reason": error.get("code"),
        },
        metadata=metadata,
    )


def _map_execution_result(tool_call: ToolCall, execution: ToolExecutionResult) -> ToolResult:
    envelope = envelope_from_execution(execution)
    return _tool_result_from_envelope(
        tool_call,
        envelope,
        execution_mode=execution.execution_mode.value,
        reason=execution.reason,
    )


def build_tool_call_limit_exceeded_result(tool_call: ToolCall) -> ToolResult:
    return _envelope_error_result(
        tool_call,
        code=ToolExecutionErrorCode.EXECUTION_FAILED,
        message="Too many tool calls in one round",
        execution_mode=ToolExecutionMode.NO_OP.value,
        reason="tool_call_limit_exceeded",
    )


def _envelope_error_result(
    tool_call: ToolCall,
    *,
    code: ToolExecutionErrorCode,
    message: str,
    execution_mode: str,
    reason: str | None = None,
) -> ToolResult:
    envelope = build_tool_error(tool_call.name, code=code, message=message)
    return sanitize_tool_result(
        _tool_result_from_envelope(
            tool_call,
            envelope,
            execution_mode=execution_mode,
            reason=reason or code.value,
        ),
    )


def _envelope_code_for_access_decision(decision: ToolAccessDecision) -> ToolExecutionErrorCode:
    if decision.reason_code == ToolAccessReasonCode.TOOL_NOT_FOUND:
        return ToolExecutionErrorCode.NOT_FOUND
    if decision.reason_code == ToolAccessReasonCode.UNSUPPORTED_TOOL:
        return ToolExecutionErrorCode.UNSUPPORTED_TOOL
    if decision.reason_code in {
        ToolAccessReasonCode.TOOL_DISABLED,
        ToolAccessReasonCode.TOOLS_DISABLED_FOR_AGENT,
        ToolAccessReasonCode.TOOL_DENIED_BY_POLICY,
        ToolAccessReasonCode.TOOL_NOT_IN_ALLOWLIST,
        ToolAccessReasonCode.WRITE_TOOL_NOT_ALLOWED,
        ToolAccessReasonCode.AGENT_TYPE_NOT_ALLOWED,
        ToolAccessReasonCode.EXECUTION_MODE_NOT_ALLOWED,
        ToolAccessReasonCode.PROJECT_OWNERSHIP_INVALID,
        ToolAccessReasonCode.WRITE_TOOLS_DISABLED,
        ToolAccessReasonCode.WRITE_TOOL_DISABLED,
        ToolAccessReasonCode.TOOL_NOT_ALLOWED_FOR_AGENT_TYPE,
    }:
        return ToolExecutionErrorCode.PERMISSION_DENIED
    return ToolExecutionErrorCode.EXECUTION_FAILED


def _result_from_access_decision(
    tool_call: ToolCall,
    decision: ToolAccessDecision,
) -> ToolResult:
    metadata: dict[str, Any] = {
        "execution_mode": decision.execution_mode.value,
        "reason": decision.audit_reason,
        "permission_reason_code": decision.reason_code.value,
    }

    if decision.use_envelope and not decision.allowed:
        envelope_result = _envelope_error_result(
            tool_call,
            code=_envelope_code_for_access_decision(decision),
            message=decision.message,
            execution_mode=decision.execution_mode.value,
            reason=decision.audit_reason,
        )
        envelope_result.metadata["permission_reason_code"] = decision.reason_code.value
        return envelope_result

    if not decision.allowed and decision.result_status == "failed":
        return sanitize_tool_result(
            ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                status="failed",
                error={
                    "error_type": decision.reason_code.value,
                    "safe_message": decision.message,
                    "reason": decision.audit_reason,
                },
                metadata=metadata,
            ),
        )

    return sanitize_tool_result(
        ToolResult(
            call_id=tool_call.id,
            name=tool_call.name,
            status="skipped",
            output={
                "reason": decision.audit_reason,
                "tool_name": tool_call.name,
                "tool_call_id": tool_call.id,
                "safe_message": decision.message,
            },
            metadata=metadata,
        ),
    )


class SafeNoOpToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        memory_service: MemoryService | None = None,
        audit_service: ToolExecutionLogService | None = None,
        session: Any | None = None,
    ) -> None:
        self._registry = registry or get_tool_registry()
        self._memory_search = (
            MemorySearchToolExecutor(memory_service) if memory_service is not None else None
        )
        self._project_context = (
            ProjectContextGetToolExecutor(session) if session is not None else None
        )
        self._task_get = TaskGetToolExecutor(session) if session is not None else None
        self._task_list_recent = (
            TaskListRecentToolExecutor(session) if session is not None else None
        )
        self._marketing_brief_get = (
            MarketingBriefGetToolExecutor(session) if session is not None else None
        )
        self._marketing_brief_list = (
            MarketingBriefListToolExecutor(session) if session is not None else None
        )
        self._content_asset_get = (
            ContentAssetGetToolExecutor(session) if session is not None else None
        )
        self._content_asset_list = (
            ContentAssetListToolExecutor(session) if session is not None else None
        )
        self._campaign_asset_list = (
            CampaignAssetListToolExecutor(session) if session is not None else None
        )
        self._marketing_campaign_get = (
            MarketingCampaignGetToolExecutor(session) if session is not None else None
        )
        self._marketing_campaign_list = (
            MarketingCampaignListToolExecutor(session) if session is not None else None
        )
        self._marketing_campaign_overview = (
            MarketingCampaignOverviewToolExecutor(session) if session is not None else None
        )
        self._marketing_campaign_workflow = (
            MarketingCampaignWorkflowToolExecutor(session) if session is not None else None
        )
        self._review_queue_list = (
            ReviewQueueListToolExecutor(session) if session is not None else None
        )
        self._content_asset_create_draft = (
            ContentAssetCreateDraftToolExecutor(session) if session is not None else None
        )
        self._content_asset_create_revision = (
            ContentAssetCreateRevisionToolExecutor(session)
            if session is not None
            else None
        )
        self._campaign_plan_draft_create = (
            CampaignPlanDraftCreateToolExecutor(session) if session is not None else None
        )
        self._campaign_plan_draft_generate_assets = (
            CampaignPlanDraftGenerateAssetsToolExecutor(session)
            if session is not None
            else None
        )
        self._publication_calendar_list = (
            PublicationCalendarListToolExecutor(session) if session is not None else None
        )
        self._marketing_funnel_get = (
            MarketingFunnelGetToolExecutor(session) if session is not None else None
        )
        self._marketing_funnel_list = (
            MarketingFunnelListToolExecutor(session) if session is not None else None
        )
        self._marketing_funnel_step_assets = (
            MarketingFunnelStepAssetsToolExecutor(session) if session is not None else None
        )
        self._marketing_funnel_gap_analysis = (
            MarketingFunnelGapAnalysisToolExecutor(session) if session is not None else None
        )
        self._audit_service = audit_service

    async def execute(self, tool_call: ToolCall, context: ToolExecutionContext) -> ToolResult:
        started_at = time.perf_counter()
        result = await self._execute_impl(tool_call, context)
        if self._audit_service is not None:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            await self._record_audit(context, tool_call, result, duration_ms)
        return result

    async def _record_audit(
        self,
        context: ToolExecutionContext,
        tool_call: ToolCall,
        result: ToolResult,
        duration_ms: int,
    ) -> None:
        try:
            await self._audit_service.record_execution(
                context,
                tool_call,
                result,
                duration_ms,
            )
        except Exception as exc:
            self._audit_service.note_audit_failure(context)
            log.warning(
                "tool_audit.record_failed",
                tool_name=tool_call.name,
                agent_run_id=str(context.agent_run_id),
                error_type=type(exc).__name__,
            )

    async def _execute_impl(self, tool_call: ToolCall, context: ToolExecutionContext) -> ToolResult:
        access = evaluate_tool_access(
            agent_type=context.agent_type,
            tool_name=tool_call.name,
            context=context,
            registry=self._registry,
        )
        if not access.allowed:
            return _result_from_access_decision(tool_call, access)

        tool = access.tool
        assert tool is not None

        if is_real_read_only_executable(tool_call.name) or is_real_write_executable(
            tool_call.name,
        ):
            validation = validate_tool_arguments(tool, tool_call.arguments)
            if not validation.ok:
                execution_mode = (
                    ToolExecutionMode.WRITE.value
                    if is_real_write_executable(tool_call.name)
                    else ToolExecutionMode.READ_ONLY.value
                )
                return _envelope_error_result(
                    tool_call,
                    code=ToolExecutionErrorCode.INVALID_ARGUMENTS,
                    message=validation.message,
                    execution_mode=execution_mode,
                    reason="invalid_arguments",
                )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "memory.search"
            and self._memory_search is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._memory_search.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "project_context.get"
            and self._project_context is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._project_context.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "task.get"
            and self._task_get is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._task_get.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "task.list_recent"
            and self._task_list_recent is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._task_list_recent.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_brief.get"
            and self._marketing_brief_get is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_brief_get.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_brief.list"
            and self._marketing_brief_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_brief_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "content_asset.get"
            and self._content_asset_get is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._content_asset_get.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "content_asset.list"
            and self._content_asset_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._content_asset_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "campaign_asset.list"
            and self._campaign_asset_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._campaign_asset_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_campaign.get"
            and self._marketing_campaign_get is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_campaign_get.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_campaign.list"
            and self._marketing_campaign_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_campaign_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_campaign.overview"
            and self._marketing_campaign_overview is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_campaign_overview.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_campaign.workflow"
            and self._marketing_campaign_workflow is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_campaign_workflow.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "review_queue.list"
            and self._review_queue_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._review_queue_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "publication_calendar.list"
            and self._publication_calendar_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._publication_calendar_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_write_executable(tool_call.name)
            and tool_call.name == "content_asset.create_draft"
            and self._content_asset_create_draft is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._content_asset_create_draft.execute(tool_call, context),
                execution_mode=ToolExecutionMode.WRITE.value,
            )

        if (
            is_real_write_executable(tool_call.name)
            and tool_call.name == "content_asset.create_revision"
            and self._content_asset_create_revision is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._content_asset_create_revision.execute(tool_call, context),
                execution_mode=ToolExecutionMode.WRITE.value,
            )

        if (
            is_real_write_executable(tool_call.name)
            and tool_call.name == "campaign_plan_draft.create"
            and self._campaign_plan_draft_create is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._campaign_plan_draft_create.execute(tool_call, context),
                execution_mode=ToolExecutionMode.WRITE.value,
            )

        if (
            is_real_write_executable(tool_call.name)
            and tool_call.name == "campaign_plan_draft.generate_assets"
            and self._campaign_plan_draft_generate_assets is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._campaign_plan_draft_generate_assets.execute(tool_call, context),
                execution_mode=ToolExecutionMode.WRITE.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_funnel.get"
            and self._marketing_funnel_get is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_funnel_get.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_funnel.list"
            and self._marketing_funnel_list is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_funnel_list.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_funnel.step_assets"
            and self._marketing_funnel_step_assets is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_funnel_step_assets.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_read_only_executable(tool_call.name)
            and tool_call.name == "marketing_funnel.gap_analysis"
            and self._marketing_funnel_gap_analysis is not None
        ):
            return await self._execute_real_tool(
                tool_call,
                context,
                lambda: self._marketing_funnel_gap_analysis.execute(tool_call, context),
                execution_mode=ToolExecutionMode.READ_ONLY.value,
            )

        if (
            is_real_write_executable(tool_call.name)
            or is_real_read_only_executable(tool_call.name)
        ):
            return _envelope_error_result(
                tool_call,
                code=ToolExecutionErrorCode.UNSUPPORTED_TOOL,
                message="Tool execution is not available",
                execution_mode=ToolExecutionMode.NO_OP.value,
                reason="tool_execution_disabled",
            )

        return sanitize_tool_result(
            ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                status="skipped",
                output={
                    "reason": "tool_execution_disabled",
                    "tool_name": tool_call.name,
                    "tool_call_id": tool_call.id,
                },
                metadata={"execution_mode": ToolExecutionMode.NO_OP.value},
            ),
        )

    async def _execute_real_tool(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
        execute_fn: Any,
        *,
        execution_mode: str,
    ) -> ToolResult:
        try:
            execution = await execute_fn()
            return sanitize_tool_result(_map_execution_result(tool_call, execution))
        except Exception as exc:
            code, message = normalize_tool_error(exc, tool_name=tool_call.name)
            log.warning(
                "tool_execution.unexpected_error",
                tool_name=tool_call.name,
                agent_run_id=str(context.agent_run_id),
                error_type=type(exc).__name__,
            )
            return _envelope_error_result(
                tool_call,
                code=code,
                message=message,
                execution_mode=execution_mode,
                reason=code.value,
            )
