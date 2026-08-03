"""Write tool: campaign_plan_draft.create (Phase 10.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.services.campaign_plan_draft_service import CampaignPlanDraftService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CAMPAIGN_PLAN_DRAFT_FORBIDDEN_ARGUMENT_KEYS,
    format_campaign_plan_draft_create_result,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class CampaignPlanDraftCreateOptions:
    project_id: UUID
    campaign_id: UUID
    title: str
    plan_payload: dict[str, Any]


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


def parse_campaign_plan_draft_create_arguments(
    arguments: dict[str, Any],
) -> CampaignPlanDraftCreateOptions:
    tool_name = CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
    for forbidden_key in CAMPAIGN_PLAN_DRAFT_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"{tool_name} does not accept argument: {forbidden_key}",
                tool_name=tool_name,
                original_error_type="InvalidToolArguments",
            )

    plan_payload = arguments.get("plan_payload")
    if not isinstance(plan_payload, dict):
        raise ToolValidationError(
            f"{tool_name} plan_payload must be an object",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    title_raw = arguments.get("title")
    if not isinstance(title_raw, str) or not title_raw.strip():
        raise ToolValidationError(
            f"{tool_name} requires a non-empty title string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    title = title_raw.strip()
    if len(title) > 512:
        raise ToolValidationError(
            f"{tool_name} title must be at most 512 characters",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    return CampaignPlanDraftCreateOptions(
        project_id=_parse_uuid(
            arguments.get("project_id"),
            field_name="project_id",
            tool_name=tool_name,
        ),
        campaign_id=_parse_uuid(
            arguments.get("campaign_id"),
            field_name="campaign_id",
            tool_name=tool_name,
        ),
        title=sanitize_text(title),
        plan_payload=plan_payload,
    )


class CampaignPlanDraftCreateToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._drafts = CampaignPlanDraftService(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        tool_name = CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME
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
            options = parse_campaign_plan_draft_create_arguments(tool_call.arguments)
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
            row = await self._drafts.create(
                context.owner_id,
                options.project_id,
                options.campaign_id,
                title=options.title,
                plan_payload=options.plan_payload,
                source_agent_run_id=context.agent_run_id,
            )
        except InvalidStateError as exc:
            message = str(exc)
            reason = "campaign_archived"
            if "plan_payload" in message.lower() or "invalid plan" in message.lower():
                reason = "invalid_plan_payload"
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason=reason,
                error_payload={
                    "error_type": "InvalidState",
                    "safe_message": message,
                    "reason": reason,
                },
            )

        if row is None:
            return ToolExecutionResult(
                **base,
                status=ToolExecutionStatus.FAILED,
                reason="campaign_not_found",
                error_payload={
                    "error_type": "CampaignNotFound",
                    "safe_message": "Campaign or agent run not found",
                    "reason": "campaign_not_found",
                },
            )

        payload = format_campaign_plan_draft_create_result(row)
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload={"draft": payload, "count": 1},
            reason=None,
        )
