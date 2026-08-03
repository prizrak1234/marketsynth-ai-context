"""Safe audit logging for marketing data tool calls (Phase AI.221)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.schemas.contracts import MarketingToolCallStatus, MarketingToolType

log = get_logger(__name__)


def log_marketing_tool_call(
    *,
    call_id: str,
    project_id: str,
    tool_type: MarketingToolType,
    status: MarketingToolCallStatus,
    safe_metadata: dict[str, object] | None = None,
    error: str | None = None,
) -> None:
    log.info(
        "marketing_tool_call_audit",
        call_id=call_id,
        project_id=project_id,
        tool_type=tool_type.value,
        status=status.value,
        safe_metadata=safe_metadata or {},
        error=error,
    )
