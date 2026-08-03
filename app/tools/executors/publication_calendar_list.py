"""Read-only publication_calendar.list tool executor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.publishing.contracts import PublicationJobStatus
from app.services.publication_calendar_service import PublicationCalendarService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.errors import ToolValidationError
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.executors.task_get import _validate_context
from app.tools.marketing_tools import (
    MARKETING_FORBIDDEN_ARGUMENT_KEYS,
    PUBLICATION_CALENDAR_LIST_DEFAULT_LIMIT,
    PUBLICATION_CALENDAR_LIST_MAX_LIMIT,
    PUBLICATION_CALENDAR_LIST_TOOL_NAME,
)
from app.tools.permissions import ToolExecutionMode


@dataclass(frozen=True)
class PublicationCalendarListOptions:
    from_at: datetime | None = None
    to_at: datetime | None = None
    channel_id: UUID | None = None
    campaign_id: UUID | None = None
    status: PublicationJobStatus | None = None
    limit: int = PUBLICATION_CALENDAR_LIST_DEFAULT_LIMIT


def _coerce_int(value: object, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    raise ToolValidationError(
        f"publication_calendar.list {field_name} must be an integer",
        tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
        original_error_type="InvalidToolArguments",
    )


def _parse_uuid(value: object, *, field_name: str) -> UUID | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            f"publication_calendar.list {field_name} must be a non-empty string UUID",
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise ToolValidationError(
            f"publication_calendar.list {field_name} must be a valid UUID",
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc


def _parse_dt(value: object, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            f"publication_calendar.list {field_name} must be an ISO datetime string",
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ToolValidationError(
            f"publication_calendar.list {field_name} must be an ISO datetime string",
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        ) from exc
    if parsed.tzinfo is None:
        raise ToolValidationError(
            f"publication_calendar.list {field_name} must be UTC-aware",
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )
    return parsed.astimezone(UTC)


def parse_publication_calendar_list_arguments(
    arguments: dict[str, Any],
) -> PublicationCalendarListOptions:
    for forbidden_key in MARKETING_FORBIDDEN_ARGUMENT_KEYS:
        if forbidden_key in arguments:
            raise ToolValidationError(
                f"publication_calendar.list does not accept argument: {forbidden_key}",
                tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )

    limit = _coerce_int(
        arguments.get("limit"),
        field_name="limit",
        default=PUBLICATION_CALENDAR_LIST_DEFAULT_LIMIT,
    )
    if limit < 1 or limit > PUBLICATION_CALENDAR_LIST_MAX_LIMIT:
        raise ToolValidationError(
            (
                "publication_calendar.list limit must be between 1 and "
                f"{PUBLICATION_CALENDAR_LIST_MAX_LIMIT}"
            ),
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )

    status: PublicationJobStatus | None = None
    raw_status = arguments.get("status")
    if raw_status is not None:
        if not isinstance(raw_status, str) or not raw_status.strip():
            raise ToolValidationError(
                "publication_calendar.list status must be a non-empty string",
                tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            )
        try:
            status = PublicationJobStatus(raw_status.strip())
        except ValueError as exc:
            raise ToolValidationError(
                "publication_calendar.list status is invalid",
                tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
                original_error_type="InvalidToolArguments",
            ) from exc

    from_at = _parse_dt(arguments.get("from_at"), field_name="from_at")
    to_at = _parse_dt(arguments.get("to_at"), field_name="to_at")
    if from_at is not None and to_at is not None and to_at < from_at:
        raise ToolValidationError(
            "publication_calendar.list to_at must be >= from_at",
            tool_name=PUBLICATION_CALENDAR_LIST_TOOL_NAME,
            original_error_type="InvalidToolArguments",
        )

    return PublicationCalendarListOptions(
        from_at=from_at,
        to_at=to_at,
        channel_id=_parse_uuid(arguments.get("channel_id"), field_name="channel_id"),
        campaign_id=_parse_uuid(arguments.get("campaign_id"), field_name="campaign_id"),
        status=status,
        limit=limit,
    )


class PublicationCalendarListToolExecutor:
    def __init__(self, session: AsyncSession) -> None:
        self._calendar = PublicationCalendarService(session)

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        base = {
            "tool_name": PUBLICATION_CALENDAR_LIST_TOOL_NAME,
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
            options = parse_publication_calendar_list_arguments(tool_call.arguments)
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

        items = await self._calendar.list_calendar(
            context.owner_id,
            context.project_id,
            from_at=options.from_at,
            to_at=options.to_at,
            channel_id=options.channel_id,
            campaign_id=options.campaign_id,
            status=options.status,
            limit=options.limit,
        )
        def _dt(value: object) -> str | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
            return str(value)

        normalized = []
        for item in items:
            entry = dict(item)
            entry["scheduled_at"] = _dt(entry.get("scheduled_at"))
            entry["queued_at"] = _dt(entry.get("queued_at"))
            normalized.append(entry)

        payload = {"items": normalized, "count": len(normalized)}
        return ToolExecutionResult(
            **base,
            status=ToolExecutionStatus.SUCCEEDED,
            output_payload=payload,
            reason=None,
        )

