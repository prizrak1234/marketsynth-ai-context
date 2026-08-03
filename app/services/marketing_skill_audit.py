"""Safe audit logging for marketing skill runs (Phase AI.228)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.schemas.contracts import MarketingSkillRunStatus, MarketingSkillType

log = get_logger(__name__)


def log_marketing_skill_run(
    *,
    run_id: str,
    project_id: str,
    skill_type: MarketingSkillType,
    status: MarketingSkillRunStatus,
    safe_metadata: dict[str, object] | None = None,
    used_tool_call_ids: list[str] | None = None,
    error: str | None = None,
) -> None:
    log.info(
        "marketing_skill_run_audit",
        run_id=run_id,
        project_id=project_id,
        skill_type=skill_type.value,
        status=status.value,
        safe_metadata=safe_metadata or {},
        used_tool_call_ids=used_tool_call_ids or [],
        error=error,
    )
