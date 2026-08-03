"""Marketing funnel read-only tool definitions, schemas, and safe payload helpers."""

from __future__ import annotations

from typing import Any

from app.core.security import sanitize_text
from app.marketing.contracts import ContentAssetStatus
from app.marketing.funnel_contracts import FunnelStepType, MarketingFunnelStatus

MARKETING_FUNNEL_GET_TOOL_NAME = "marketing_funnel.get"
MARKETING_FUNNEL_LIST_TOOL_NAME = "marketing_funnel.list"
MARKETING_FUNNEL_STEP_ASSETS_TOOL_NAME = "marketing_funnel.step_assets"
MARKETING_FUNNEL_GAP_ANALYSIS_TOOL_NAME = "marketing_funnel.gap_analysis"

FUNNEL_FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "owner_id",
        "project_id",
        "agent_id",
        "agent_run_id",
        "run_id",
        "task_id",
    },
)

MARKETING_FUNNEL_LIST_MAX_LIMIT = 10
MARKETING_FUNNEL_LIST_DEFAULT_LIMIT = 5

FUNNEL_DESCRIPTION_MAX_CHARS = 2_000

CANONICAL_FUNNEL_STEP_TYPES: tuple[FunnelStepType, ...] = (
    FunnelStepType.AWARENESS,
    FunnelStepType.LEAD_MAGNET,
    FunnelStepType.NURTURE,
    FunnelStepType.OFFER,
    FunnelStepType.CHECKOUT,
    FunnelStepType.ONBOARDING,
    FunnelStepType.RETENTION,
    FunnelStepType.REACTIVATION,
)

MARKETING_FUNNEL_GET_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "funnel_id": {"type": "string"},
        "include_steps": {"type": "boolean", "default": True},
    },
    "required": ["funnel_id"],
    "additionalProperties": False,
}

MARKETING_FUNNEL_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MARKETING_FUNNEL_LIST_MAX_LIMIT,
            "default": MARKETING_FUNNEL_LIST_DEFAULT_LIMIT,
        },
        "include_archived": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
}

MARKETING_FUNNEL_STEP_ASSETS_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "step_id": {"type": "string"},
    },
    "required": ["step_id"],
    "additionalProperties": False,
}

MARKETING_FUNNEL_GAP_ANALYSIS_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "funnel_id": {"type": "string"},
    },
    "required": ["funnel_id"],
    "additionalProperties": False,
}


def _status_value(status: object) -> str:
    return getattr(status, "value", str(status))


def sanitize_funnel_description(description: str) -> str:
    sanitized = sanitize_text(description or "")
    if len(sanitized) <= FUNNEL_DESCRIPTION_MAX_CHARS:
        return sanitized
    return sanitized[:FUNNEL_DESCRIPTION_MAX_CHARS]


def format_funnel_step_compact(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "step_type": _status_value(row.step_type),
        "title": row.title,
        "position": row.position,
        "status": _status_value(row.status),
    }


def format_funnel_get_payload(
    funnel: object,
    *,
    steps: list[object] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(funnel.id),
        "brief_id": str(funnel.brief_id) if funnel.brief_id is not None else None,
        "title": funnel.title,
        "description": sanitize_funnel_description(funnel.description or ""),
        "status": _status_value(funnel.status),
        "steps_count": len(steps) if steps is not None else 0,
    }
    if steps is not None:
        payload["steps"] = [format_funnel_step_compact(step) for step in steps]
    return payload


def format_funnel_list_item(row: object, *, steps_count: int) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "brief_id": str(row.brief_id) if row.brief_id is not None else None,
        "title": row.title,
        "description": sanitize_funnel_description(row.description or ""),
        "status": _status_value(row.status),
        "steps_count": steps_count,
    }


def format_funnel_step_assets_step(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "step_type": _status_value(row.step_type),
        "title": row.title,
    }


def format_funnel_step_asset_item(link: object) -> dict[str, Any]:
    return {
        "id": str(link.asset_id),
        "title": link.asset_title,
        "type": link.asset_type,
        "status": link.asset_status,
        "role": _status_value(link.role),
    }


def parse_marketing_funnel_status(value: object, *, tool_name: str) -> MarketingFunnelStatus | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        from app.tools.errors import ToolValidationError

        raise ToolValidationError(
            f"{tool_name} status must be a non-empty string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    try:
        return MarketingFunnelStatus(value.strip().lower())
    except ValueError as exc:
        from app.tools.errors import ToolValidationError

        raise ToolValidationError(
            f"{tool_name} status must be a valid marketing funnel status",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        ) from exc


def compute_funnel_gap_analysis(
    *,
    steps: list[object],
    links: list[object],
    linked_assets_by_id: dict[object, object],
) -> dict[str, Any]:
    """Heuristic gap analysis — no LLM."""
    active_steps = [
        step
        for step in steps
        if _status_value(step.status) != "archived"
    ]
    present_types = {_status_value(step.step_type) for step in active_steps}
    canonical_values = [_status_value(step_type) for step_type in CANONICAL_FUNNEL_STEP_TYPES]
    missing_steps = [value for value in canonical_values if value not in present_types]

    links_by_step: dict[object, list[object]] = {}
    for link in links:
        links_by_step.setdefault(link.step_id, []).append(link)

    steps_without_assets = [
        _status_value(step.step_type)
        for step in active_steps
        if not links_by_step.get(step.id)
    ]

    approved_assets_count = 0
    draft_assets_count = 0
    seen_asset_ids: set[object] = set()
    for link in links:
        if link.asset_id in seen_asset_ids:
            continue
        seen_asset_ids.add(link.asset_id)
        asset = linked_assets_by_id.get(link.asset_id)
        if asset is None:
            continue
        asset_status = _status_value(asset.status)
        if asset_status == ContentAssetStatus.APPROVED.value:
            approved_assets_count += 1
        elif asset_status == ContentAssetStatus.DRAFT.value:
            draft_assets_count += 1

    coverage_score = round(
        (len(canonical_values) - len(missing_steps)) / len(canonical_values),
        2,
    )

    return {
        "missing_steps": missing_steps,
        "steps_without_assets": steps_without_assets,
        "approved_assets_count": approved_assets_count,
        "draft_assets_count": draft_assets_count,
        "coverage_score": coverage_score,
    }
