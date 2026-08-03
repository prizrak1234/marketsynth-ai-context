"""Marketing read-only tool definitions, schemas, and safe payload helpers."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.security import sanitize_text
from app.llm.secrets_boundary import find_sensitive_key
from app.marketing.contracts import ContentAssetStatus, ContentAssetType, MarketingBriefStatus
from app.schemas.marketing_campaigns import CampaignWorkflowResponse
from app.tools.errors import ToolValidationError
from app.tools.security import find_forbidden_tool_key, sanitize_tool_payload

MARKETING_BRIEF_GET_TOOL_NAME = "marketing_brief.get"
MARKETING_BRIEF_LIST_TOOL_NAME = "marketing_brief.list"
CONTENT_ASSET_GET_TOOL_NAME = "content_asset.get"
CONTENT_ASSET_LIST_TOOL_NAME = "content_asset.list"
CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME = "content_asset.create_draft"
CONTENT_ASSET_CREATE_REVISION_TOOL_NAME = "content_asset.create_revision"
CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME = "campaign_plan_draft.create"
CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME = "campaign_plan_draft.generate_assets"
MARKETING_CAMPAIGN_GET_TOOL_NAME = "marketing_campaign.get"
MARKETING_CAMPAIGN_LIST_TOOL_NAME = "marketing_campaign.list"
MARKETING_CAMPAIGN_OVERVIEW_TOOL_NAME = "marketing_campaign.overview"
MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME = "marketing_campaign.workflow"
PUBLICATION_CALENDAR_LIST_TOOL_NAME = "publication_calendar.list"

MARKETING_FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "owner_id",
        "project_id",
        "agent_id",
        "agent_run_id",
        "run_id",
        "task_id",
    },
)

MARKETING_BRIEF_LIST_MAX_LIMIT = 10
MARKETING_BRIEF_LIST_DEFAULT_LIMIT = 5
CONTENT_ASSET_LIST_MAX_LIMIT = 10
CONTENT_ASSET_LIST_DEFAULT_LIMIT = 5
MARKETING_CAMPAIGN_LIST_MAX_LIMIT = 10
MARKETING_CAMPAIGN_LIST_DEFAULT_LIMIT = 5
PUBLICATION_CALENDAR_LIST_MAX_LIMIT = 10
PUBLICATION_CALENDAR_LIST_DEFAULT_LIMIT = 5

OFFER_PREVIEW_MAX_CHARS = 160
BODY_PREVIEW_MAX_CHARS = 300
BODY_INCLUDE_MAX_CHARS = 4_000

MARKETING_BRIEF_GET_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "brief_id": {"type": "string"},
        "include_constraints": {"type": "boolean", "default": True},
    },
    "required": ["brief_id"],
    "additionalProperties": False,
}

MARKETING_BRIEF_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MARKETING_BRIEF_LIST_MAX_LIMIT,
            "default": MARKETING_BRIEF_LIST_DEFAULT_LIMIT,
        },
        "include_archived": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
}

CONTENT_ASSET_GET_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "asset_id": {"type": "string"},
        "include_body": {"type": "boolean", "default": False},
    },
    "required": ["asset_id"],
    "additionalProperties": False,
}

CONTENT_ASSET_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "brief_id": {"type": "string"},
        "campaign_id": {"type": "string"},
        "type": {"type": "string"},
        "status": {"type": "string"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": CONTENT_ASSET_LIST_MAX_LIMIT,
            "default": CONTENT_ASSET_LIST_DEFAULT_LIMIT,
        },
        "include_archived": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
}

CAMPAIGN_ASSET_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_id": {"type": "string"},
        "type": {"type": "string"},
        "status": {"type": "string"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": CONTENT_ASSET_LIST_MAX_LIMIT,
            "default": CONTENT_ASSET_LIST_DEFAULT_LIMIT,
        },
        "include_archived": {"type": "boolean", "default": False},
    },
    "required": ["campaign_id"],
    "additionalProperties": False,
}

METADATA_PREVIEW_MAX_KEYS = 20
METADATA_PREVIEW_MAX_JSON_BYTES = 1024
METADATA_PREVIEW_MAX_SCALAR_CHARS = 120

CREATE_DRAFT_FORBIDDEN_ARGUMENT_KEYS = MARKETING_FORBIDDEN_ARGUMENT_KEYS | frozenset(
    {
        "status",
        "source_asset_id",
        "source_version_number",
        "revision_number",
    },
)

CONTENT_ASSET_CREATE_DRAFT_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "brief_id": {"type": "string"},
        "type": {
            "type": "string",
            "enum": [
                "landing_page",
                "ad_copy",
                "email",
                "telegram_post",
                "article",
                "offer",
                "audience_profile",
                "funnel_step",
            ],
        },
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
        },
        "body": {
            "type": "string",
            "minLength": 1,
        },
        "metadata": {
            "type": "object",
            "default": {},
        },
    },
    "required": ["type", "title", "body"],
    "additionalProperties": False,
}

CREATE_DRAFT_METADATA_MAX_KEYS = 32
CREATE_DRAFT_METADATA_MAX_JSON_BYTES = 2_048

CREATE_REVISION_FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "owner_id",
        "agent_id",
        "agent_run_id",
        "run_id",
        "task_id",
        "source_agent_run_id",
        "brief_id",
        "campaign_id",
        "status",
        "source_asset_id",
        "source_version_number",
        "revision_number",
    },
)

CONTENT_ASSET_CREATE_REVISION_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string"},
        "asset_id": {"type": "string"},
        "title": {"type": "string"},
        "body": {"type": "string", "minLength": 1},
        "metadata_patch": {
            "type": "object",
            "default": {},
        },
    },
    "required": ["project_id", "asset_id", "body"],
    "additionalProperties": False,
}

REVISION_METADATA_PATCH_MAX_KEYS = 32
REVISION_METADATA_PATCH_MAX_JSON_BYTES = 2_048

CAMPAIGN_PLAN_DRAFT_FORBIDDEN_ARGUMENT_KEYS = frozenset(
    {
        "owner_id",
        "agent_id",
        "agent_run_id",
        "run_id",
        "task_id",
        "source_agent_run_id",
    },
)

CAMPAIGN_PLAN_DRAFT_CREATE_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string"},
        "campaign_id": {"type": "string"},
        "title": {"type": "string", "minLength": 1, "maxLength": 512},
        "plan_payload": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "target_audience": {"type": "string"},
                "key_message": {"type": "string"},
                "content_items": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        },
    },
    "required": ["project_id", "campaign_id", "title", "plan_payload"],
    "additionalProperties": False,
}

CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_id": {"type": "string"},
        "draft_id": {"type": "string"},
    },
    "required": ["campaign_id", "draft_id"],
    "additionalProperties": False,
}

MARKETING_CAMPAIGN_GET_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_id": {"type": "string"},
    },
    "required": ["campaign_id"],
    "additionalProperties": False,
}

MARKETING_CAMPAIGN_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MARKETING_CAMPAIGN_LIST_MAX_LIMIT,
            "default": MARKETING_CAMPAIGN_LIST_DEFAULT_LIMIT,
        },
        "include_archived": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
}

MARKETING_CAMPAIGN_OVERVIEW_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_id": {"type": "string"},
    },
    "required": ["campaign_id"],
    "additionalProperties": False,
}

MARKETING_CAMPAIGN_WORKFLOW_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "campaign_id": {"type": "string"},
    },
    "required": ["campaign_id"],
    "additionalProperties": False,
}

PUBLICATION_CALENDAR_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "from_at": {"type": "string"},
        "to_at": {"type": "string"},
        "channel_id": {"type": "string"},
        "campaign_id": {"type": "string"},
        "status": {"type": "string"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": PUBLICATION_CALENDAR_LIST_MAX_LIMIT,
            "default": PUBLICATION_CALENDAR_LIST_DEFAULT_LIMIT,
        },
    },
    "additionalProperties": False,
}


def truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars]


def offer_preview(offer: str) -> str:
    return truncate_text(offer, OFFER_PREVIEW_MAX_CHARS)


def body_preview(body: str) -> str:
    sanitized = sanitize_text(body or "")
    return truncate_text(sanitized, BODY_PREVIEW_MAX_CHARS)


def body_for_include(body: str) -> str:
    sanitized = sanitize_text(body or "")
    return truncate_text(sanitized, BODY_INCLUDE_MAX_CHARS)


def _status_value(status: object) -> str:
    return getattr(status, "value", str(status))


def format_marketing_brief_full(
    row: object,
    *,
    include_constraints: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "title": row.title,
        "product_description": row.product_description,
        "target_audience": row.target_audience,
        "offer": row.offer,
        "goals": list(row.goals or []),
        "status": _status_value(row.status),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
    if include_constraints:
        payload["constraints"] = dict(row.constraints or {})
    return payload


def format_marketing_brief_compact(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "title": row.title,
        "offer_preview": offer_preview(row.offer or ""),
        "status": _status_value(row.status),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _content_asset_revision_fields(row: object) -> dict[str, Any]:
    source_asset_id = getattr(row, "source_asset_id", None)
    return {
        "source_asset_id": str(source_asset_id) if source_asset_id is not None else None,
        "source_version_number": getattr(row, "source_version_number", None),
        "revision_number": getattr(row, "revision_number", None),
    }


def _content_asset_campaign_id(row: object) -> str | None:
    campaign_id = getattr(row, "campaign_id", None)
    return str(campaign_id) if campaign_id is not None else None


def format_content_asset_metadata_preview(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Safe metadata for agent tools — no secrets, bounded size."""
    raw = dict(metadata or {})
    if not raw:
        return {}
    if find_sensitive_key(raw) is not None:
        keys = sorted(str(key) for key in raw)[:METADATA_PREVIEW_MAX_KEYS]
        return {"_redacted": True, "keys": keys}

    sanitized = sanitize_tool_payload(raw)
    preview: dict[str, Any] = {}
    for key, value in list(sanitized.items())[:METADATA_PREVIEW_MAX_KEYS]:
        if isinstance(value, str):
            preview[key] = (
                value[:METADATA_PREVIEW_MAX_SCALAR_CHARS]
                if len(value) > METADATA_PREVIEW_MAX_SCALAR_CHARS
                else value
            )
        elif isinstance(value, (int, float, bool)) or value is None:
            preview[key] = value
        else:
            preview[key] = type(value).__name__

    encoded = json.dumps(preview, ensure_ascii=True, sort_keys=True).encode("utf-8")
    if len(encoded) > METADATA_PREVIEW_MAX_JSON_BYTES:
        return {"keys": sorted(preview.keys())[:METADATA_PREVIEW_MAX_KEYS]}
    return preview


def coerce_optional_uuid_argument(
    value: object,
    *,
    field_name: str,
    tool_name: str,
) -> UUID | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            f"{tool_name} {field_name} must be a non-empty string",
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


def coerce_required_uuid_argument(
    value: object,
    *,
    field_name: str,
    tool_name: str,
) -> UUID:
    parsed = coerce_optional_uuid_argument(
        value,
        field_name=field_name,
        tool_name=tool_name,
    )
    if parsed is None:
        raise ToolValidationError(
            f"{tool_name} requires a non-empty {field_name} string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    return parsed


def format_content_asset_full(
    row: object,
    *,
    include_body: bool,
) -> dict[str, Any]:
    raw_body = row.body or ""
    preview = body_preview(raw_body)
    payload: dict[str, Any] = {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "brief_id": str(row.brief_id) if row.brief_id is not None else None,
        "campaign_id": _content_asset_campaign_id(row),
        "task_id": str(row.task_id) if row.task_id is not None else None,
        "agent_run_id": str(row.agent_run_id) if row.agent_run_id is not None else None,
        "type": _status_value(row.asset_type),
        "title": row.title,
        "status": _status_value(row.status),
        "current_version_number": row.current_version_number,
        "approved_version_number": row.approved_version_number,
        **_content_asset_revision_fields(row),
        "metadata": format_content_asset_metadata_preview(dict(row.asset_metadata or {})),
        "body_preview": preview,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
    if include_body:
        payload["body"] = body_for_include(raw_body)
    return payload


def format_campaign_plan_draft_create_result(row: object) -> dict[str, Any]:
    status = getattr(row.status, "value", str(row.status))
    return {
        "draft_id": str(row.id),
        "campaign_id": str(row.campaign_id),
        "status": status,
        "created_at": row.created_at.isoformat(),
    }


def format_campaign_plan_draft_generate_assets_result(result: object) -> dict[str, Any]:
    return {
        "created_count": int(result.created_count),
        "already_generated": bool(result.already_generated),
        "asset_ids": [str(asset_id) for asset_id in result.asset_ids],
    }


def validate_revision_metadata_patch(
    value: object,
    *,
    tool_name: str,
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ToolValidationError(
            f"{tool_name} metadata_patch must be an object",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    forbidden = find_forbidden_tool_key(value)
    if forbidden is not None:
        raise ToolValidationError(
            f"{tool_name} metadata_patch contains forbidden key: {forbidden}",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    if find_sensitive_key(value) is not None:
        raise ToolValidationError(
            f"{tool_name} metadata_patch contains sensitive key",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    sanitized = sanitize_tool_payload(dict(value))
    if len(sanitized) > REVISION_METADATA_PATCH_MAX_KEYS:
        raise ToolValidationError(
            f"{tool_name} metadata_patch exceeds {REVISION_METADATA_PATCH_MAX_KEYS} keys",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    encoded = json.dumps(sanitized, ensure_ascii=True, sort_keys=True).encode("utf-8")
    if len(encoded) > REVISION_METADATA_PATCH_MAX_JSON_BYTES:
        raise ToolValidationError(
            f"{tool_name} metadata_patch is too large",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    return sanitized


def reject_secrets_in_revision_body(body: str, *, tool_name: str) -> None:
    lowered = body.lower()
    secret_markers = ("api_key=", "bearer ", "sk-", "password=", "authorization:")
    if any(marker in lowered for marker in secret_markers):
        raise ToolValidationError(
            f"{tool_name} body must not contain secret-like content",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )


def format_content_asset_create_revision_result(row: object) -> dict[str, Any]:
    return {
        "asset_id": str(row.id),
        "status": _status_value(row.status),
        "current_version_number": row.current_version_number,
        "approved_version_number": row.approved_version_number,
    }


def format_content_asset_create_draft_result(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "brief_id": str(row.brief_id) if row.brief_id is not None else None,
        "task_id": str(row.task_id) if row.task_id is not None else None,
        "agent_run_id": str(row.agent_run_id) if row.agent_run_id is not None else None,
        "type": _status_value(row.asset_type),
        "title": row.title,
        "status": _status_value(row.status),
        "current_version_number": row.current_version_number,
        "body_preview": body_preview(row.body or ""),
        "created_at": row.created_at.isoformat(),
    }


def format_content_asset_compact(row: object) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "brief_id": str(row.brief_id) if row.brief_id is not None else None,
        "campaign_id": _content_asset_campaign_id(row),
        "type": _status_value(row.asset_type),
        "title": row.title,
        "status": _status_value(row.status),
        "current_version_number": row.current_version_number,
        "approved_version_number": row.approved_version_number,
        **_content_asset_revision_fields(row),
        "metadata": format_content_asset_metadata_preview(dict(row.asset_metadata or {})),
        "body_preview": body_preview(row.body or ""),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def format_marketing_campaign_workflow_compact(
    workflow: CampaignWorkflowResponse,
) -> dict[str, Any]:
    """Compact workflow dashboard — counts and state only (no plan/asset bodies)."""
    return {
        "campaign_id": str(workflow.campaign_id),
        "workflow_state": workflow.workflow_state.value,
        "next_recommended_action": workflow.next_recommended_action.value,
        "counts": workflow.counts.model_dump(mode="json"),
    }


def format_marketing_campaign_safe(row: object) -> dict[str, Any]:
    """Safe campaign payload for agent tools (no campaign_metadata)."""
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "brief_id": str(row.brief_id) if getattr(row, "brief_id", None) is not None else None,
        "title": row.title,
        "description": row.description,
        "status": _status_value(row.status),
        "start_at": (
            row.start_at.isoformat() if getattr(row, "start_at", None) is not None else None
        ),
        "end_at": row.end_at.isoformat() if getattr(row, "end_at", None) is not None else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def parse_marketing_brief_status(value: object, *, tool_name: str) -> MarketingBriefStatus | None:
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
        return MarketingBriefStatus(value.strip().lower())
    except ValueError as exc:
        from app.tools.errors import ToolValidationError

        raise ToolValidationError(
            f"{tool_name} status must be a valid marketing brief status",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        ) from exc


def parse_content_asset_status(value: object, *, tool_name: str) -> ContentAssetStatus | None:
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
        return ContentAssetStatus(value.strip().lower())
    except ValueError as exc:
        from app.tools.errors import ToolValidationError

        raise ToolValidationError(
            f"{tool_name} status must be a valid content asset status",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        ) from exc


def parse_content_asset_type(value: object, *, tool_name: str) -> ContentAssetType | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        from app.tools.errors import ToolValidationError

        raise ToolValidationError(
            f"{tool_name} type must be a non-empty string",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    try:
        return ContentAssetType(value.strip().lower())
    except ValueError as exc:
        from app.tools.errors import ToolValidationError

        raise ToolValidationError(
            f"{tool_name} type must be a valid content asset type",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        ) from exc


def sanitize_create_draft_metadata(value: object, *, tool_name: str) -> dict[str, Any]:
    import json

    from app.tools.errors import ToolValidationError
    from app.tools.security import find_forbidden_tool_key, sanitize_tool_payload

    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ToolValidationError(
            f"{tool_name} metadata must be an object",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    forbidden = find_forbidden_tool_key(value)
    if forbidden is not None:
        raise ToolValidationError(
            f"{tool_name} metadata contains forbidden key: {forbidden}",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    sanitized = sanitize_tool_payload(dict(value))
    if len(sanitized) > CREATE_DRAFT_METADATA_MAX_KEYS:
        raise ToolValidationError(
            f"{tool_name} metadata exceeds {CREATE_DRAFT_METADATA_MAX_KEYS} keys",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )

    encoded = json.dumps(sanitized, ensure_ascii=True, sort_keys=True).encode("utf-8")
    if len(encoded) > CREATE_DRAFT_METADATA_MAX_JSON_BYTES:
        raise ToolValidationError(
            f"{tool_name} metadata is too large",
            tool_name=tool_name,
            original_error_type="InvalidToolArguments",
        )
    return sanitized
