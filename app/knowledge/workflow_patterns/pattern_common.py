"""Shared pattern builders for KB-WPL core library (does not modify pilot artifacts)."""

from __future__ import annotations

from typing import Any

ARCHIVE_ID = "arc-bots-knowledge-rar"
PROGRAM_PHASE_CORE = "KB-WPL-01.3B"


def core_prov(source_id: str) -> dict[str, str]:
    return {
        "source_type": "pattern_extraction_core",
        "archive_id": ARCHIVE_ID,
        "source_id": source_id,
        "program_phase": PROGRAM_PHASE_CORE,
    }


def core_variant(provider: str, component: str = "integration") -> dict[str, Any]:
    return {
        "provider": provider,
        "component": component,
        "documented_version": "source_catalog_0.1.0",
        "documented_at": "2026-07-23",
        "verification_status": "source_documented",
        "requires_reverification": True,
        "notes": "Observed in frozen catalog metadata only; not executed in core build.",
        "provenance": core_prov(f"variant-{provider}"),
    }


def core_gates(pattern_id: str) -> list[dict[str, Any]]:
    base = core_prov(f"gates-{pattern_id}")
    titles = {
        "schema_valid": "Pattern validates against workflow-pattern schema",
        "source_support_valid": "Source support gate satisfied",
        "provider_neutral": "Main flow uses functional abstractions only",
        "no_credentials": "No credential identifiers in pattern body",
        "approval_boundary_valid": "Approval boundaries match sensitivity",
        "evidence_boundary_valid": "Evidence requirements documented",
        "tenant_boundary_valid": "Tenant scope preserved",
        "idempotency_valid": "Idempotency policy matches retry behavior",
        "error_path_present": "Terminal error path documented",
        "limitations_documented": "Known limitations listed",
        "manual_review_complete": "Manual core audit complete",
    }
    return [
        {
            "gate_id": f"{pattern_id}-{gate_key}",
            "title": title,
            "description": title,
            "severity": "blocking",
            "verification_status": "source_documented",
            "provenance": base,
        }
        for gate_key, title in titles.items()
    ]


def core_step(
    step_id: str,
    step_name: str,
    step_type: str,
    security_class: str,
    **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "step_id": step_id,
        "step_name": step_name,
        "step_type": step_type,
        "security_class": security_class,
    }
    row.update(extra)
    return row


def core_edge(
    edge_id: str,
    from_step_id: str,
    to_step_id: str,
    **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "edge_id": edge_id,
        "from_step_id": from_step_id,
        "to_step_id": to_step_id,
    }
    row.update(extra)
    return row


def base_core_pattern(
    *,
    pattern_id: str,
    pattern_name: str,
    pattern_category: str,
    objective: str,
    problem_context: str,
    capability_ids: list[str],
    source_workflow_ids: list[str],
    source_practice_ids: list[str],
    steps: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    security_class: str,
    publication_sensitive: bool,
    billing_sensitive: bool,
    destructive: bool,
    approval_requirements: dict[str, Any],
    evidence_requirements: dict[str, Any],
    idempotency_requirements: dict[str, Any],
    retry_policy: str,
    error_paths: list[str],
    known_limitations: list[str],
    implementation_variants: list[dict[str, Any]],
    input_contract: dict[str, Any] | None = None,
    output_contract: dict[str, Any] | None = None,
    rate_limit_policy: str = "provider_default",
    rollback_or_recovery: str = "manual_review",
) -> dict[str, Any]:
    return {
        "pattern_id": pattern_id,
        "pattern_name": pattern_name,
        "pattern_category": pattern_category,
        "objective": objective,
        "problem_context": problem_context,
        "capability_ids": capability_ids,
        "related_skill_ids": ["ms.skill.n8n_workflow_architecture"],
        "input_contract": input_contract
        or {"type": "object", "required": ["tenant_context", "correlation_id"]},
        "output_contract": output_contract
        or {"type": "object", "required": ["status", "evidence_refs"]},
        "steps": steps,
        "edges": edges,
        "required_connectors": [],
        "required_tools": [],
        "approval_requirements": approval_requirements,
        "evidence_requirements": evidence_requirements,
        "idempotency_requirements": idempotency_requirements,
        "retry_policy": retry_policy,
        "timeout_policy": "core_default_120s",
        "rate_limit_policy": rate_limit_policy,
        "error_paths": error_paths,
        "rollback_or_recovery": rollback_or_recovery,
        "security_class": security_class,
        "tenant_scope": "tenant_scoped",
        "personal_data_class": "unknown",
        "publication_sensitive": publication_sensitive,
        "billing_sensitive": billing_sensitive,
        "destructive": destructive,
        "implementation_variants": implementation_variants,
        "source_workflow_ids": source_workflow_ids,
        "source_practice_ids": source_practice_ids,
        "known_limitations": known_limitations,
        "quality_gates": core_gates(pattern_id),
        "maturity": "reviewed",
        "provenance": core_prov(pattern_id),
    }
