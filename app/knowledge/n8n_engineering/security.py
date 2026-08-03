"""Shared security rejection rules for n8n Engineering Skills."""

from __future__ import annotations

import json
import re
from typing import Any

FORBIDDEN_SECRET_KEYS = frozenset(
    {
        "api_key",
        "password",
        "oauth_token",
        "bearer_token",
        "private_key",
        "secret",
        "token",
        "credential_value",
    }
)

FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "workflow_json",
        "activation_request",
        "deployment_result",
        "credential_value",
        "execution_status",
        "approval_granted",
        "live_patch",
        "workflow_update",
        "node_execution",
        "credential_rotation",
        "deployed",
        "activated",
        "deployment_id",
        "activation_result",
        "api_response",
    }
)

SECRET_PATTERNS = re.compile(
    r"(sk-[a-zA-Z0-9]{10,}|Bearer\s+\S+|-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----)",
    re.I,
)

UNSANITIZED_LOG_MARKERS = re.compile(
    r"(password=|api_key=|Authorization:\s*Bearer|credential_value)",
    re.I,
)


def contains_forbidden_secret(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    blob = json.dumps(payload).lower()
    for key in FORBIDDEN_SECRET_KEYS:
        if f'"{key}"' in blob:
            errors.append(f"forbidden_secret_key:{key}")
    if SECRET_PATTERNS.search(json.dumps(payload)):
        errors.append("forbidden_secret_pattern")
    return errors


def reject_forbidden_fields(
    payload: dict[str, Any],
    *,
    extra_forbidden: frozenset[str] | None = None,
) -> list[str]:
    forbidden = FORBIDDEN_FIELD_NAMES | (extra_forbidden or frozenset())
    errors: list[str] = []
    for key in payload:
        if key in forbidden:
            errors.append(f"forbidden_field:{key}")
    return errors


def reject_unsanitized_logs(payload: dict[str, Any]) -> list[str]:
    logs = payload.get("sanitized_execution_logs") or payload.get("execution_logs") or ""
    if isinstance(logs, str) and UNSANITIZED_LOG_MARKERS.search(logs):
        return ["unsanitized_execution_logs"]
    if "execution_logs" in payload and "sanitized_execution_logs" not in payload:
        return ["raw_execution_logs_forbidden"]
    return []
