"""Read-only content diff helpers (Phase 4.6)."""

from __future__ import annotations

import difflib
from collections.abc import Mapping
from typing import Any

DEFAULT_MAX_DIFF_LINES = 300

_SECRET_METADATA_KEYS = frozenset(
    {
        "api_key",
        "secret",
        "token",
        "password",
        "credential",
        "credentials",
        "authorization",
        "cookie",
    },
)
_SECRET_METADATA_SUFFIXES = (
    "_api_key",
    "_secret",
    "_token",
    "_password",
    "_credential",
    "_credentials",
    "_authorization",
    "_cookie",
)
_SECRET_VALUE_MARKERS = ("sk-", "api_key", "authorization", "bearer ")


def _is_secret_metadata_key(key: str) -> bool:
    lower = key.lower()
    if lower in _SECRET_METADATA_KEYS:
        return True
    return any(lower.endswith(suffix) for suffix in _SECRET_METADATA_SUFFIXES)


def _redact_secret_value(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in _SECRET_VALUE_MARKERS):
            return "[REDACTED]"
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _redact_secret_value(item)
            for key, item in value.items()
            if not _is_secret_metadata_key(str(key))
        }
    if isinstance(value, list):
        return [_redact_secret_value(item) for item in value]
    return value


def _metadata_for_diff(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {
        str(key): _redact_secret_value(value)
        for key, value in metadata.items()
        if not _is_secret_metadata_key(str(key))
    }


def build_text_diff(
    old_text: str,
    new_text: str,
    *,
    max_lines: int = DEFAULT_MAX_DIFF_LINES,
) -> dict[str, Any]:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    if not old_lines and old_text:
        old_lines = [old_text if old_text.endswith("\n") else f"{old_text}\n"]
    if not new_lines and new_text:
        new_lines = [new_text if new_text.endswith("\n") else f"{new_text}\n"]

    unified = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="old",
            tofile="new",
            lineterm="",
        ),
    )
    truncated = len(unified) > max_lines
    selected = unified[:max_lines] if truncated else unified
    return {
        "format": "unified",
        "truncated": truncated,
        "lines": selected,
    }


def build_metadata_diff(
    old_metadata: Mapping[str, Any] | None,
    new_metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    old_safe = _metadata_for_diff(old_metadata)
    new_safe = _metadata_for_diff(new_metadata)

    old_keys = set(old_safe)
    new_keys = set(new_safe)

    added = {key: new_safe[key] for key in sorted(new_keys - old_keys)}
    removed = {key: old_safe[key] for key in sorted(old_keys - new_keys)}
    changed: dict[str, Any] = {}
    for key in sorted(old_keys & new_keys):
        if old_safe[key] != new_safe[key]:
            changed[key] = {"old": old_safe[key], "new": new_safe[key]}

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def build_content_asset_diff(
    old_snapshot: Mapping[str, Any],
    new_snapshot: Mapping[str, Any],
    *,
    max_lines: int = DEFAULT_MAX_DIFF_LINES,
) -> dict[str, Any]:
    old_title = str(old_snapshot.get("title", ""))
    new_title = str(new_snapshot.get("title", ""))
    old_body = str(old_snapshot.get("body", ""))
    new_body = str(new_snapshot.get("body", ""))
    old_metadata = old_snapshot.get("metadata")
    new_metadata = new_snapshot.get("metadata")

    title_changed = old_title != new_title
    body_changed = old_body != new_body
    metadata_diff = build_metadata_diff(
        old_metadata if isinstance(old_metadata, Mapping) else {},
        new_metadata if isinstance(new_metadata, Mapping) else {},
    )
    metadata_changed = bool(
        metadata_diff["added"] or metadata_diff["removed"] or metadata_diff["changed"],
    )

    return {
        "title_changed": title_changed,
        "body_changed": body_changed,
        "metadata_changed": metadata_changed,
        "body_diff": build_text_diff(old_body, new_body, max_lines=max_lines),
        "metadata_diff": metadata_diff,
    }
