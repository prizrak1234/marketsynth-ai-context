"""Semantic validation for ms.skill.n8n_workflow_debugging."""

from __future__ import annotations

from typing import Any

from app.knowledge.n8n_engineering.constants import DEBUG_ERROR_CLASSES
from app.knowledge.n8n_engineering.pattern_selection import validate_pattern_selection_list
from app.knowledge.n8n_engineering.security import (
    contains_forbidden_secret,
    reject_forbidden_fields,
    reject_unsanitized_logs,
)


def validate_debugging_input(payload: dict[str, Any]) -> list[str]:
    errors = contains_forbidden_secret(payload)
    errors.extend(reject_forbidden_fields(payload))
    errors.extend(reject_unsanitized_logs(payload))
    pattern_refs = payload.get("existing_pattern_references") or []
    if pattern_refs and isinstance(pattern_refs[0], dict):
        errors.extend(validate_pattern_selection_list(pattern_refs))
    return errors


def validate_debugging_output(payload: dict[str, Any]) -> list[str]:
    errors = contains_forbidden_secret(payload)
    errors.extend(
        reject_forbidden_fields(
            payload,
            extra_forbidden=frozenset({"live_patch", "workflow_update", "credential_rotation"}),
        )
    )

    classification = payload.get("failure_classification")
    if classification and classification not in DEBUG_ERROR_CLASSES:
        errors.append("invalid_failure_classification")

    confidence = payload.get("diagnostic_confidence")
    evidence = payload.get("supporting_evidence") or []
    if confidence == "high" and not evidence:
        errors.append("missing_evidence_prevents_high_confidence")

    for candidate in payload.get("remediation_candidates") or []:
        if isinstance(candidate, dict) and candidate.get("action") in {
            "live_patch",
            "workflow_update",
            "credential_rotation",
        }:
            errors.append("live_mutation_remediation_forbidden")

    unknown_outcome = payload.get("failure_classification") == "unknown_outcome"
    for candidate in payload.get("remediation_candidates") or []:
        if (
            unknown_outcome
            and isinstance(candidate, dict)
            and candidate.get("action") == "blind_retry"
        ):
            errors.append("unknown_outcome_blind_retry_forbidden")

    sandbox = payload.get("sandbox_plan") or {}
    if sandbox.get("publication_enabled"):
        errors.append("publication_sandbox_must_remain_disabled")
    if sandbox.get("billing_enabled"):
        errors.append("billing_sandbox_must_remain_disabled")

    pattern_refs = payload.get("patterns_consulted") or []
    if pattern_refs and isinstance(pattern_refs[0], dict):
        errors.extend(validate_pattern_selection_list(pattern_refs))

    return errors
