"""Workflow pattern semantic and quality-gate validation."""

from __future__ import annotations

import json
import re
from typing import Any

from app.knowledge.workflow_patterns.contracts import (
    ManualAuditRecord,
    PatternValidationReport,
)
from app.knowledge.workflow_patterns.source_support import validate_pattern_source_support

FORBIDDEN_BODY_KEYS = frozenset(
    {"nodes", "connections", "pinData", "workflow_body", "raw_json", "settings"}
)
FORBIDDEN_MATURITY = frozenset({"active", "executable", "approved", "deployed"})
FORBIDDEN_NEUTRAL_TOKENS = re.compile(
    r"n8n-nodes-base\.|credential[_-]?id|Bearer\s+|sk-[a-zA-Z0-9]{10,}",
    re.I,
)
MANDATORY_GATE_IDS = (
    "schema_valid",
    "source_support_valid",
    "provider_neutral",
    "no_credentials",
    "approval_boundary_valid",
    "evidence_boundary_valid",
    "tenant_boundary_valid",
    "idempotency_valid",
    "error_path_present",
    "limitations_documented",
    "manual_review_complete",
)


def validate_pattern_semantics(pattern: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    maturity = pattern.get("maturity", "")
    if maturity in FORBIDDEN_MATURITY:
        errors.append(f"forbidden maturity: {maturity}")
    if maturity != "reviewed":
        errors.append("pilot maturity must be reviewed")

    for key in FORBIDDEN_BODY_KEYS:
        if key in pattern:
            errors.append(f"raw workflow body forbidden: {key}")

    blob = json.dumps(pattern)
    if FORBIDDEN_NEUTRAL_TOKENS.search(blob):
        errors.append("provider-specific or secret marker in neutral pattern body")

    steps_blob = json.dumps(pattern.get("steps", []))
    edges_blob = json.dumps(pattern.get("edges", []))
    objective = pattern.get("objective", "")
    problem = pattern.get("problem_context", "")
    neutral_blob = f"{steps_blob} {edges_blob} {objective} {problem}"
    provider_names = ("telegram", "gmail", "openai", "wordpress", "instagram", "linkedin")
    leaked = any(name in neutral_blob.lower() for name in provider_names)
    if leaked and not _provider_only_in_variants(pattern, provider_names):
        errors.append("provider name leaked outside implementation_variants")

    approval = pattern.get("approval_requirements", {})
    if pattern.get("publication_sensitive") and not approval.get("publication_approval_required"):
        errors.append("publication pattern requires publication_approval_required")
    if pattern.get("publication_sensitive") and approval.get("auto_approval_allowed"):
        errors.append("publication auto approval forbidden")
    if pattern.get("billing_sensitive") and not approval.get("spend_approval_required"):
        errors.append("billing pattern requires spend_approval_required")
    if pattern.get("destructive") and approval.get("auto_approval_allowed"):
        errors.append("destructive pattern cannot allow auto approval")

    retry = pattern.get("retry_policy", "none")
    idem = pattern.get("idempotency_requirements", {})
    if retry not in ("none", "") and not idem.get("required"):
        errors.append("retry pattern requires idempotency policy")
    if (
        idem.get("unknown_outcome_auto_retry")
        and pattern.get("security_class") in {"write_internal", "publication", "destructive"}
    ):
        errors.append("unknown-outcome write cannot auto-retry")

    if pattern.get("pattern_id") == "evidence_grounded_generation":
        if "source_reference" not in (pattern.get("evidence_requirements") or {}).get(
            "evidence_classes",
            [],
        ):
            errors.append("RAG pattern requires source_reference evidence")
        limitations = " ".join(pattern.get("known_limitations", [])).lower()
        if "injection" not in limitations and "prompt" not in limitations:
            errors.append("RAG pattern must document injection boundary")

    if pattern.get("pattern_id") == "structured_LLM_to_API_request":
        steps = pattern.get("steps", [])
        if not any(step.get("step_type") == "validate" for step in steps):
            errors.append("structured LLM/API pattern requires schema validation step")

    if not pattern.get("error_paths"):
        errors.append("error path required")
    if not pattern.get("known_limitations"):
        errors.append("limitations required")
    if not pattern.get("tenant_scope"):
        errors.append("tenant_scope required")

    gate_ids = {gate.get("gate_id", "").split("-")[-1] for gate in pattern.get("quality_gates", [])}
    for required in MANDATORY_GATE_IDS:
        if required not in gate_ids:
            errors.append(f"missing quality gate: {required}")

    return errors


def _provider_only_in_variants(pattern: dict[str, Any], provider_names: tuple[str, ...]) -> bool:
    variants_blob = json.dumps(pattern.get("implementation_variants", [])).lower()
    main_blob = json.dumps(
        {
            "steps": pattern.get("steps"),
            "edges": pattern.get("edges"),
            "objective": pattern.get("objective"),
            "problem_context": pattern.get("problem_context"),
        }
    ).lower()
    leaked = [name for name in provider_names if name in main_blob and name not in variants_blob]
    return not leaked


def validate_pilot_pattern(
    pattern: dict[str, Any],
    *,
    catalog: dict[str, Any],
    audit_records: list[ManualAuditRecord],
    schema_validate,
) -> PatternValidationReport:
    pattern_id = str(pattern.get("pattern_id", ""))
    schema_valid = True
    try:
        schema_validate(pattern)
    except Exception as exc:  # noqa: BLE001
        schema_valid = False
        semantic = [f"schema_invalid: {exc}"]
        return PatternValidationReport(
            pattern_id=pattern_id,
            schema_valid=False,
            semantic_errors=semantic,
        )

    semantic_errors = validate_pattern_semantics(pattern)
    source_support = validate_pattern_source_support(pattern, catalog, audit_records)
    if not source_support.supported:
        semantic_errors.append("source_support_invalid")
        semantic_errors.extend(source_support.blockers)

    quality_gate_errors = [
        err for err in semantic_errors if err.startswith("missing quality gate")
    ]
    return PatternValidationReport(
        pattern_id=pattern_id,
        schema_valid=schema_valid,
        semantic_errors=semantic_errors,
        quality_gate_errors=quality_gate_errors,
        source_support=source_support,
    )
