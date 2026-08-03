"""Semantic validation for ms.skill.n8n_deployment_review."""

from __future__ import annotations

from typing import Any

from app.knowledge.n8n_engineering.pattern_selection import validate_pattern_selection_list
from app.knowledge.n8n_engineering.security import (
    contains_forbidden_secret,
    reject_forbidden_fields,
)


def validate_deployment_input(payload: dict[str, Any]) -> list[str]:
    errors = contains_forbidden_secret(payload)
    errors.extend(reject_forbidden_fields(payload))
    return errors


def validate_deployment_output(payload: dict[str, Any]) -> list[str]:
    errors = contains_forbidden_secret(payload)
    errors.extend(
        reject_forbidden_fields(
            payload,
            extra_forbidden=frozenset(
                {"deployed", "activated", "deployment_id", "activation_result", "approval_granted"}
            ),
        )
    )

    pattern_refs = payload.get("patterns_consulted") or []
    if pattern_refs and isinstance(pattern_refs[0], dict):
        errors.extend(validate_pattern_selection_list(pattern_refs))

    readiness = payload.get("deployment_readiness")
    publication = payload.get("publication_findings") or {}
    ready_states = {"ready_for_manual_deployment", "ready_with_conditions"}
    if (
        publication.get("publication_configured")
        and publication.get("approval_missing")
        and readiness in ready_states
    ):
        errors.append("publication_without_approval_blocked")

    billing = payload.get("billing_findings") or {}
    if (
        billing.get("billing_configured")
        and not billing.get("budget_context_present")
        and readiness in ready_states
    ):
        errors.append("billing_without_budget_blocked")

    retry = payload.get("retry_and_idempotency_findings") or {}
    if retry.get("retry_enabled") and not retry.get("idempotency_present"):
        errors.append("retry_without_idempotency_blocked")

    rollback = payload.get("rollback_findings") or {}
    if readiness == "ready_for_manual_deployment" and rollback.get("rollback_plan_missing"):
        errors.append("missing_rollback_blocks_ready")

    tests = payload.get("test_evidence_findings") or {}
    if readiness == "ready_for_manual_deployment" and tests.get("tests_missing"):
        errors.append("missing_tests_blocks_ready")

    provider = payload.get("provider_compatibility_findings") or {}
    if (
        provider.get("unknown_version")
        and readiness == "ready_for_manual_deployment"
        and not payload.get("warnings")
        and not payload.get("blockers")
    ):
        errors.append("unknown_provider_version_requires_condition")

    gate = payload.get("activation_gate") or {}
    if gate.get("final_manual_action_required") is False:
        errors.append("final_manual_action_required_must_be_true")

    if payload.get("approval_granted") is True:
        errors.append("approval_granted_forbidden")

    return errors
