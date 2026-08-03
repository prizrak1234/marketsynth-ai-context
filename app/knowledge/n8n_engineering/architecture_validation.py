"""Semantic validation for ms.skill.n8n_workflow_architecture."""

from __future__ import annotations

from typing import Any

from app.knowledge.n8n_engineering.pattern_selection import validate_pattern_selection_list
from app.knowledge.n8n_engineering.security import (
    contains_forbidden_secret,
    reject_forbidden_fields,
)

PUBLICATION_PATTERNS = frozenset(
    {"human_approval_before_publication", "publication_confirmation"}
)
STRUCTURED_LLM_PATTERNS = frozenset({
    "structured_LLM_to_API_request",
    "quality_gate_after_generation",
})
RETRY_PATTERNS = frozenset({"retry_with_idempotency", "provider_rate_limit_handling"})


def validate_architecture_input(payload: dict[str, Any]) -> list[str]:
    errors = contains_forbidden_secret(payload)
    errors.extend(reject_forbidden_fields(payload))
    if payload.get("credentials_required") and isinstance(payload.get("credential_values"), dict):
        errors.append("credential_values_forbidden")
    catalog_hash = payload.get("workflow_pattern_library_hash") or payload.get(
        "source_catalog_hash"
    )
    if catalog_hash and catalog_hash != payload.get("source_catalog_hash"):
        errors.append("catalog_hash_inconsistent")
    pattern_refs = payload.get("selected_pattern_ids") or payload.get("pattern_references") or []
    if pattern_refs and isinstance(pattern_refs[0], dict):
        errors.extend(validate_pattern_selection_list(pattern_refs))
    return errors


def validate_architecture_output(payload: dict[str, Any]) -> list[str]:
    errors = contains_forbidden_secret(payload)
    errors.extend(reject_forbidden_fields(payload))
    if "workflow_json" in payload:
        errors.append("workflow_json_forbidden")

    pattern_refs = payload.get("pattern_references") or []
    errors.extend(validate_pattern_selection_list(pattern_refs))

    publication = payload.get("publication_context") or {}
    if publication.get("enabled") or publication.get("publication_required"):
        pattern_ids = {ref.get("pattern_id") for ref in pattern_refs}
        if not pattern_ids & PUBLICATION_PATTERNS:
            errors.append("publication_requires_approval_pattern")

    retry = payload.get("retry_requirements") or payload.get("retry_plan") or {}
    if retry.get("enabled") or retry.get("write_retry"):
        pattern_ids = {ref.get("pattern_id") for ref in pattern_refs}
        if not pattern_ids & RETRY_PATTERNS:
            errors.append("write_retry_requires_idempotency_pattern")

    llm_api = payload.get("provider_constraints") or {}
    if isinstance(llm_api, list):
        llm_api_flag = any(isinstance(item, dict) and item.get("llm_to_api") for item in llm_api)
    else:
        llm_api_flag = bool(llm_api.get("llm_to_api"))
    if llm_api_flag:
        pattern_ids = {ref.get("pattern_id") for ref in pattern_refs}
        if not pattern_ids & STRUCTURED_LLM_PATTERNS:
            errors.append("llm_to_api_requires_structured_validation_pattern")

    error_paths = payload.get("error_paths") or []
    readiness = payload.get("architecture_readiness")
    if readiness == "ready_for_implementation_review" and not error_paths:
        errors.append("missing_error_path_blocks_ready")

    provider_constraints = payload.get("provider_constraints") or []
    if isinstance(provider_constraints, list):
        for constraint in provider_constraints:
            if (
                isinstance(constraint, dict)
                and constraint.get("requires_reverification") is False
                and not constraint.get("documented_version")
            ):
                errors.append("unknown_provider_version_requires_reverification")

    if (
        payload.get("provider_reverification_required")
        and readiness == "ready_for_implementation_review"
        and not payload.get("unknowns")
        and not payload.get("assumptions")
    ):
        pass  # reverification flag alone is acceptable

    return errors
