"""ProjectBrief fingerprint and content normalization (Commercial MVP P0.1)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.schemas.contracts import ProjectBriefContent


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_value(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return value


def content_for_fingerprint(content: ProjectBriefContent) -> dict[str, Any]:
    """Business-relevant payload only — excludes ids/timestamps/status/sync."""
    payload = content.model_dump(mode="json")
    return _normalize_value(payload)


def compute_project_brief_fingerprint(content: ProjectBriefContent) -> str:
    canonical = json.dumps(
        content_for_fingerprint(content),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
