"""Sanitize beta feedback safe_context (Phase AI.91)."""

from __future__ import annotations

from typing import Any

from app.publishing_foundation.safe_metadata import sanitize_publishing_metadata

_ALLOWED_KEYS = frozenset(
    {
        "step",
        "screen",
        "route",
        "error_code",
        "job_id",
        "project_id",
        "plan_id",
        "channel_type",
        "browser",
        "app_version",
    },
)


def sanitize_feedback_context(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned = sanitize_publishing_metadata(raw)
    return {key: cleaned[key] for key in cleaned if key in _ALLOWED_KEYS}
