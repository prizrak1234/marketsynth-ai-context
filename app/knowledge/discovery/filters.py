"""Input filtering and security rejection."""

from __future__ import annotations

import json
from typing import Any

from app.knowledge.discovery.contracts import (
    EXECUTION_SENSITIVITIES,
    FORBIDDEN_RECOMMENDED_ACTIONS,
    MAX_RESULT_LIMIT,
    QUERY_MODES,
    SAFE_NEXT_ACTIONS,
    SECRET_PATTERNS,
)
from app.knowledge.discovery.errors import DiscoverySecurityError, DiscoveryValidationError

WORKFLOW_BODY_MARKERS = ('"nodes":', '"connections":', "n8n-nodes-base.")


def reject_sensitive_input(payload: dict[str, Any]) -> None:
    blob = json.dumps(payload, ensure_ascii=False).lower()
    for marker in SECRET_PATTERNS:
        if marker in blob:
            raise DiscoverySecurityError(f"sensitive_input:{marker}")
    if any(marker in blob for marker in WORKFLOW_BODY_MARKERS):
        raise DiscoverySecurityError("raw_workflow_body_forbidden")


def validate_query(query: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("query_id", "task_description", "tenant_id", "provenance"):
        if not query.get(field):
            errors.append(f"missing_query_field:{field}")
    if query.get("include_quarantined") and not query.get("internal_audit_mode"):
        errors.append("quarantined_requires_audit_mode")
    sensitivity = query.get("execution_sensitivity", "none")
    if sensitivity not in EXECUTION_SENSITIVITIES:
        errors.append("invalid_execution_sensitivity")
    limit = query.get("result_limit", 10)
    if not isinstance(limit, int) or limit < 1 or limit > MAX_RESULT_LIMIT:
        errors.append("invalid_result_limit")
    mode = query.get("mode", "task_routing")
    if mode not in QUERY_MODES:
        errors.append("invalid_mode")
    try:
        reject_sensitive_input(query)
    except DiscoverySecurityError as exc:
        errors.append(str(exc))
    return errors


def validate_recommended_action(action: str) -> list[str]:
    if action in FORBIDDEN_RECOMMENDED_ACTIONS:
        return [f"forbidden_action:{action}"]
    if action not in SAFE_NEXT_ACTIONS:
        return [f"unknown_safe_action:{action}"]
    return []


def validate_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("runtime_authorized") is not False:
        errors.append("runtime_authorized_must_be_false")
    for action in result.get("safe_next_actions") or []:
        if isinstance(action, str):
            errors.extend(validate_recommended_action(action))
        elif isinstance(action, dict) and action.get("action"):
            errors.extend(validate_recommended_action(action["action"]))
    for candidate in (
        (result.get("skill_candidates") or [])
        + (result.get("pattern_candidates") or [])
        + (result.get("capabilities") or [])
    ):
        if isinstance(candidate, dict) and candidate.get("runtime_authorized") is True:
            errors.append("candidate_runtime_authorized")
    return errors


def raise_if_invalid(errors: list[str]) -> None:
    if errors:
        raise DiscoveryValidationError(";".join(errors))
