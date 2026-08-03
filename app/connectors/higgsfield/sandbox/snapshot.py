"""Sanitized sandbox artifact I/O for Higgsfield MCP verification."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SANDBOX_ROOT = (
    Path(__file__).resolve().parents[4] / "packages" / "connectors" / "higgsfield" / "sandbox"
)

_SECRET_KEY_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "api_key",
    "authorization",
    "credential",
    "cookie",
    "bearer",
    "access_token",
    "refresh_token",
    "auth",
)
_SIGNED_URL_QUERY_RE = re.compile(r"([?&])([^=&]+)=([^&]+)", re.IGNORECASE)


def sanitize_snapshot_payload(data: Any) -> Any:
    """Recursively redact secrets and sensitive URL query params."""
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = sanitize_snapshot_payload(value)
        return cleaned
    if isinstance(data, list):
        return [sanitize_snapshot_payload(item) for item in data]
    if isinstance(data, str):
        if data.strip().lower().startswith("bearer "):
            return "[REDACTED]"
        return _redact_signed_url_query(data)
    return data


def _redact_signed_url_query(value: str) -> str:
    if "://" not in value or "?" not in value:
        return value

    def _replacer(match: re.Match[str]) -> str:
        param = match.group(2).lower()
        if any(fragment in param for fragment in ("token", "sig", "signature", "key", "auth")):
            return f"{match.group(1)}{match.group(2)}=[REDACTED]"
        return match.group(0)

    return _SIGNED_URL_QUERY_RE.sub(_replacer, value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sanitize_snapshot_payload(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_tools_snapshot() -> dict[str, Any]:
    path = SANDBOX_ROOT / "tools_snapshot.json"
    if not path.is_file():
        return {"status": "sandbox_verification_required", "tools": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_sandbox_artifacts(
    *,
    server_capabilities: dict[str, Any],
    tools_snapshot: dict[str, Any],
    tool_schema_hashes: dict[str, str],
    operation_mapping: dict[str, Any],
    authentication_findings: dict[str, Any],
    freeze_manifest: dict[str, Any],
) -> None:
    _write_json(SANDBOX_ROOT / "server_capabilities.json", server_capabilities)
    _write_json(SANDBOX_ROOT / "tools_snapshot.json", tools_snapshot)
    _write_json(SANDBOX_ROOT / "tool_schema_hashes.json", tool_schema_hashes)
    _write_json(SANDBOX_ROOT / "operation_mapping.json", operation_mapping)
    _write_json(SANDBOX_ROOT / "authentication_findings.json", authentication_findings)
    _write_json(SANDBOX_ROOT / "freeze_manifest.json", freeze_manifest)
