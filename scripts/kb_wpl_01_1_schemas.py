#!/usr/bin/env python3
# ruff: noqa: E501
"""KB-WPL-01.1 — Generate workflow_patterns shared schema bundle."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
URI_BASE = "https://schemas.marketsynth.ai/workflow-patterns/0.1.0/"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema(id_name: str, title: str, props: dict, required: list[str], *, defs: dict | None = None) -> dict:
    doc: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{URI_BASE}{id_name}",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "properties": props,
        "required": required,
    }
    if defs:
        doc["$defs"] = defs
    return doc


PROVENANCE = {
    "source_type": {"type": "string"},
    "source_id": {"type": "string"},
    "archive_id": {"type": "string"},
    "archive_hash": {"type": "string", "minLength": 64, "maxLength": 64},
    "relative_path": {"type": "string"},
    "content_hash": {"type": "string", "minLength": 64, "maxLength": 64},
    "generated_at": {"type": "string"},
    "program_phase": {"type": "string"},
}

PROVENANCE_REQ = ["source_type", "archive_id"]

REF_PROVENANCE = {"$ref": "provenance.schema.json"}

APPROVAL_REQUIREMENTS = {
    "human_approval_required": {"type": "boolean"},
    "approval_gates": {
        "type": "array",
        "items": {
            "type": "string",
            "enum": [
                "before_write",
                "before_publication",
                "before_spend",
                "before_activation",
                "before_destructive_action",
                "before_external_action",
            ],
        },
    },
    "auto_approval_allowed": {"type": "boolean"},
    "spend_approval_required": {"type": "boolean"},
    "publication_approval_required": {"type": "boolean"},
}

EVIDENCE_REQUIREMENTS = {
    "required": {"type": "boolean"},
    "evidence_classes": {
        "type": "array",
        "items": {
            "type": "string",
            "enum": [
                "source_reference",
                "execution_log",
                "approval_record",
                "test_result",
                "audit_finding",
                "user_statement",
            ],
        },
    },
    "minimum_evidence_count": {"type": "integer", "minimum": 0},
}

IDEMPOTENCY_POLICY = {
    "required": {"type": "boolean"},
    "policy": {
        "type": "string",
        "enum": [
            "none",
            "dedupe_by_event_id",
            "dedupe_by_content_hash",
            "at_least_once_with_compensation",
            "manual_reconciliation",
        ],
    },
    "unknown_outcome_auto_retry": {"type": "boolean"},
    "duplicate_event_prevention": {"type": "boolean"},
}

SECURITY_CLASS = {
    "type": "string",
    "enum": ["read_only", "write_internal", "publication", "billing", "destructive", "elevated_review"],
}

MATURITY = {
    "type": "string",
    "enum": [
        "extracted",
        "normalized",
        "reviewed",
        "regression_tested",
        "platform_adapted",
        "deprecated",
        "rejected",
    ],
}

VERIFICATION_STATUS = {
    "type": "string",
    "enum": [
        "claimed",
        "source_documented",
        "reproduced",
        "regression_tested",
        "contradicted",
        "obsolete",
        "unknown",
    ],
}

SCHEMAS: dict[str, dict] = {
    "provenance.schema.json": schema(
        "provenance.schema.json",
        "Provenance",
        PROVENANCE,
        PROVENANCE_REQ,
    ),
    "source-reference.schema.json": schema(
        "source-reference.schema.json",
        "SourceReference",
        {
            "archive_id": {"type": "string"},
            "archive_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            "relative_path": {"type": "string"},
            "content_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            "source_category": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        ["archive_id", "relative_path", "content_hash", "provenance"],
    ),
    "security-finding.schema.json": schema(
        "security-finding.schema.json",
        "SecurityFinding",
        {
            "finding_id": {"type": "string"},
            "severity": {"type": "string", "enum": ["info", "low", "medium", "high", "critical"]},
            "finding_type": {"type": "string"},
            "location": {"type": "string"},
            "description": {"type": "string"},
            "redacted": {"type": "boolean"},
            "provenance": REF_PROVENANCE,
        },
        ["finding_id", "severity", "finding_type", "description", "redacted", "provenance"],
    ),
    "provider-constraint.schema.json": schema(
        "provider-constraint.schema.json",
        "ProviderConstraint",
        {
            "provider": {"type": "string"},
            "component": {"type": "string"},
            "documented_version": {"type": "string"},
            "documented_at": {"type": "string"},
            "verification_status": VERIFICATION_STATUS,
            "requires_reverification": {"type": "boolean"},
            "notes": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        [
            "provider",
            "documented_version",
            "documented_at",
            "verification_status",
            "requires_reverification",
            "provenance",
        ],
    ),
    "capability-reference.schema.json": schema(
        "capability-reference.schema.json",
        "CapabilityReference",
        {
            "capability_id": {"type": "string"},
            "capability_name": {"type": "string"},
            "profession_id": {"type": "string"},
            "notes": {"type": "string"},
        },
        ["capability_id", "capability_name"],
    ),
    "connector-requirement.schema.json": schema(
        "connector-requirement.schema.json",
        "ConnectorRequirement",
        {
            "connector_id": {"type": "string"},
            "connector_type": {"type": "string"},
            "required": {"type": "boolean"},
            "approval_required": {"type": "boolean"},
            "notes": {"type": "string"},
        },
        ["connector_id", "connector_type", "required"],
    ),
    "tool-requirement.schema.json": schema(
        "tool-requirement.schema.json",
        "ToolRequirement",
        {
            "tool_id": {"type": "string"},
            "tool_action": {"type": "string"},
            "required": {"type": "boolean"},
            "approval_required": {"type": "boolean"},
            "security_class": SECURITY_CLASS,
            "notes": {"type": "string"},
        },
        ["tool_id", "tool_action", "required", "security_class"],
    ),
    "quality-gate.schema.json": schema(
        "quality-gate.schema.json",
        "QualityGate",
        {
            "gate_id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "severity": {"type": "string", "enum": ["info", "warning", "blocking"]},
            "applies_to": {"type": "array", "items": {"type": "string"}},
            "verification_status": VERIFICATION_STATUS,
            "provenance": REF_PROVENANCE,
        },
        ["gate_id", "title", "severity", "verification_status", "provenance"],
    ),
    "workflow-pattern-step.schema.json": schema(
        "workflow-pattern-step.schema.json",
        "WorkflowPatternStep",
        {
            "step_id": {"type": "string"},
            "step_name": {"type": "string"},
            "step_type": {"type": "string"},
            "description": {"type": "string"},
            "inputs": {"type": "array", "items": {"type": "string"}},
            "outputs": {"type": "array", "items": {"type": "string"}},
            "connector_requirements": {
                "type": "array",
                "items": {"$ref": "connector-requirement.schema.json"},
            },
            "tool_requirements": {
                "type": "array",
                "items": {"$ref": "tool-requirement.schema.json"},
            },
            "approval_gate": {"type": "string"},
            "security_class": SECURITY_CLASS,
        },
        ["step_id", "step_name", "step_type", "security_class"],
    ),
    "workflow-pattern-edge.schema.json": schema(
        "workflow-pattern-edge.schema.json",
        "WorkflowPatternEdge",
        {
            "edge_id": {"type": "string"},
            "from_step_id": {"type": "string"},
            "to_step_id": {"type": "string"},
            "condition": {"type": "string"},
            "on_failure": {"type": "string", "enum": ["stop", "retry", "fallback", "human_review", "dead_letter"]},
        },
        ["edge_id", "from_step_id", "to_step_id"],
    ),
    "knowledge-artifact.schema.json": schema(
        "knowledge-artifact.schema.json",
        "KnowledgeArtifact",
        {
            "artifact_id": {"type": "string"},
            "artifact_type": {"type": "string"},
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "source_reference": {"$ref": "source-reference.schema.json"},
            "content_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            "language": {"type": "string"},
            "domain": {"type": "string"},
            "capabilities": {"type": "array", "items": {"type": "string"}},
            "trust_status": {
                "type": "string",
                "enum": ["untrusted", "quarantined", "statically_validated", "methodology_approved", "rejected"],
            },
            "tenant_scope": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        [
            "artifact_id",
            "artifact_type",
            "title",
            "summary",
            "source_reference",
            "content_hash",
            "trust_status",
            "tenant_scope",
            "provenance",
        ],
    ),
    "workflow-template.schema.json": schema(
        "workflow-template.schema.json",
        "WorkflowTemplate",
        {
            "workflow_template_id": {"type": "string"},
            "original_name": {"type": "string"},
            "normalized_name": {"type": "string"},
            "source_archive_id": {"type": "string"},
            "source_path_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            "workflow_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            "topology_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            "description": {"type": "string"},
            "use_case": {"type": "string"},
            "categories": {"type": "array", "items": {"type": "string"}},
            "trigger_types": {"type": "array", "items": {"type": "string"}},
            "node_types": {"type": "array", "items": {"type": "string"}},
            "providers": {"type": "array", "items": {"type": "string"}},
            "credential_references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "credential_type": {"type": "string"},
                        "credential_id_ref": {"type": "string"},
                        "node_name": {"type": "string"},
                    },
                    "required": ["credential_type", "credential_id_ref"],
                },
            },
            "environment_references": {"type": "array", "items": {"type": "string"}},
            "side_effects": {"type": "array", "items": {"type": "string"}},
            "publication_actions": {"type": "boolean"},
            "billing_actions": {"type": "boolean"},
            "destructive_actions": {"type": "boolean"},
            "personal_data_risk": {
                "type": "string",
                "enum": ["none", "low", "elevated", "high", "unknown"],
            },
            "code_nodes": {"type": "boolean"},
            "shell_nodes": {"type": "boolean"},
            "database_nodes": {"type": "boolean"},
            "AI_nodes": {"type": "boolean"},
            "external_urls": {"type": "array", "items": {"type": "string"}},
            "security_findings": {
                "type": "array",
                "items": {"$ref": "security-finding.schema.json"},
            },
            "provider_constraints": {
                "type": "array",
                "items": {"$ref": "provider-constraint.schema.json"},
            },
            "deprecated_components": {"type": "array", "items": {"type": "string"}},
            "adaptation_status": {
                "type": "string",
                "enum": [
                    "catalog_only",
                    "reusable_pattern_candidate",
                    "requires_rewrite",
                    "rejected",
                    "deferred",
                    "superseded",
                ],
            },
            "quarantine_status": {
                "type": "string",
                "enum": ["quarantined", "reviewed", "rejected"],
            },
            "tenant_scope": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        [
            "workflow_template_id",
            "original_name",
            "normalized_name",
            "source_archive_id",
            "source_path_hash",
            "workflow_hash",
            "topology_hash",
            "categories",
            "trigger_types",
            "node_types",
            "adaptation_status",
            "quarantine_status",
            "tenant_scope",
            "provenance",
        ],
    ),
    "workflow-pattern.schema.json": schema(
        "workflow-pattern.schema.json",
        "WorkflowPattern",
        {
            "pattern_id": {"type": "string"},
            "pattern_name": {"type": "string"},
            "pattern_category": {"type": "string"},
            "objective": {"type": "string"},
            "problem_context": {"type": "string"},
            "capability_ids": {"type": "array", "items": {"type": "string"}},
            "related_skill_ids": {"type": "array", "items": {"type": "string"}},
            "input_contract": {"type": "object"},
            "output_contract": {"type": "object"},
            "steps": {
                "type": "array",
                "items": {"$ref": "workflow-pattern-step.schema.json"},
                "minItems": 1,
            },
            "edges": {
                "type": "array",
                "items": {"$ref": "workflow-pattern-edge.schema.json"},
            },
            "required_connectors": {
                "type": "array",
                "items": {"$ref": "connector-requirement.schema.json"},
            },
            "required_tools": {
                "type": "array",
                "items": {"$ref": "tool-requirement.schema.json"},
            },
            "approval_requirements": {
                "type": "object",
                "additionalProperties": False,
                "properties": APPROVAL_REQUIREMENTS,
                "required": ["human_approval_required", "auto_approval_allowed"],
            },
            "evidence_requirements": {
                "type": "object",
                "additionalProperties": False,
                "properties": EVIDENCE_REQUIREMENTS,
                "required": ["required"],
            },
            "idempotency_requirements": {
                "type": "object",
                "additionalProperties": False,
                "properties": IDEMPOTENCY_POLICY,
                "required": ["required", "policy", "unknown_outcome_auto_retry"],
            },
            "retry_policy": {"type": "string"},
            "timeout_policy": {"type": "string"},
            "rate_limit_policy": {"type": "string"},
            "error_paths": {"type": "array", "items": {"type": "string"}},
            "rollback_or_recovery": {"type": "string"},
            "security_class": SECURITY_CLASS,
            "tenant_scope": {"type": "string"},
            "personal_data_class": {
                "type": "string",
                "enum": ["none", "low", "elevated", "high", "unknown"],
            },
            "publication_sensitive": {"type": "boolean"},
            "billing_sensitive": {"type": "boolean"},
            "destructive": {"type": "boolean"},
            "implementation_variants": {
                "type": "array",
                "items": {"$ref": "provider-constraint.schema.json"},
            },
            "source_workflow_ids": {"type": "array", "items": {"type": "string"}},
            "source_practice_ids": {"type": "array", "items": {"type": "string"}},
            "known_limitations": {"type": "array", "items": {"type": "string"}},
            "quality_gates": {
                "type": "array",
                "items": {"$ref": "quality-gate.schema.json"},
            },
            "maturity": MATURITY,
            "provenance": REF_PROVENANCE,
        },
        [
            "pattern_id",
            "pattern_name",
            "pattern_category",
            "objective",
            "capability_ids",
            "steps",
            "approval_requirements",
            "evidence_requirements",
            "idempotency_requirements",
            "security_class",
            "tenant_scope",
            "publication_sensitive",
            "billing_sensitive",
            "destructive",
            "maturity",
            "provenance",
        ],
    ),
    "practice-record.schema.json": schema(
        "practice-record.schema.json",
        "PracticeRecord",
        {
            "practice_id": {"type": "string"},
            "title": {"type": "string"},
            "domain": {"type": "string"},
            "context": {"type": "string"},
            "problem": {"type": "string"},
            "recommended_practice": {"type": "string"},
            "rationale": {"type": "string"},
            "prerequisites": {"type": "array", "items": {"type": "string"}},
            "implementation_pattern": {"type": "string"},
            "failure_modes": {"type": "array", "items": {"type": "string"}},
            "security_notes": {"type": "array", "items": {"type": "string"}},
            "provider_version_scope": {
                "type": "array",
                "items": {"$ref": "provider-constraint.schema.json"},
                "minItems": 1,
            },
            "tested_environment": {"type": "string"},
            "verification_status": VERIFICATION_STATUS,
            "source_references": {
                "type": "array",
                "items": {"$ref": "source-reference.schema.json"},
            },
            "related_pattern_ids": {"type": "array", "items": {"type": "string"}},
            "tenant_scope": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        [
            "practice_id",
            "title",
            "domain",
            "problem",
            "recommended_practice",
            "provider_version_scope",
            "verification_status",
            "tenant_scope",
            "provenance",
        ],
    ),
    "error-pattern.schema.json": schema(
        "error-pattern.schema.json",
        "ErrorPattern",
        {
            "error_pattern_id": {"type": "string"},
            "platform": {"type": "string"},
            "component": {"type": "string"},
            "symptom": {"type": "string"},
            "probable_causes": {"type": "array", "items": {"type": "string"}},
            "diagnostic_steps": {"type": "array", "items": {"type": "string"}},
            "remediation_candidates": {"type": "array", "items": {"type": "string"}},
            "prevention": {"type": "array", "items": {"type": "string"}},
            "affected_versions": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "verification_status": VERIFICATION_STATUS,
            "related_practices": {"type": "array", "items": {"type": "string"}},
            "related_patterns": {"type": "array", "items": {"type": "string"}},
            "sensitive_data_warning": {"type": "boolean"},
            "tenant_scope": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        [
            "error_pattern_id",
            "platform",
            "symptom",
            "probable_causes",
            "remediation_candidates",
            "verification_status",
            "tenant_scope",
            "provenance",
        ],
    ),
    "pattern-audit-report.schema.json": schema(
        "pattern-audit-report.schema.json",
        "PatternAuditReport",
        {
            "report_id": {"type": "string"},
            "program_phase": {"type": "string"},
            "pattern_count": {"type": "integer", "minimum": 0},
            "template_count": {"type": "integer", "minimum": 0},
            "security_finding_count": {"type": "integer", "minimum": 0},
            "verdict": {
                "type": "string",
                "enum": ["READY", "CONDITIONALLY_READY", "NOT_READY"],
            },
            "invariants_checked": {"type": "integer", "minimum": 0},
            "generated_at": {"type": "string"},
            "provenance": REF_PROVENANCE,
        },
        ["report_id", "program_phase", "verdict", "provenance"],
    ),
}


def write_bundle() -> tuple[dict[str, str], str]:
    ROOT.mkdir(parents=True, exist_ok=True)
    file_hashes: dict[str, str] = {}
    ids_seen: set[str] = set()
    for name in sorted(SCHEMAS):
        doc = SCHEMAS[name]
        sid = doc["$id"]
        if sid in ids_seen:
            raise ValueError(f"duplicate $id: {sid}")
        ids_seen.add(sid)
        if not sid.startswith(URI_BASE):
            raise ValueError(f"unversioned or wrong base URI: {sid}")
        text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        path = ROOT / name
        path.write_text(text, encoding="utf-8")
        file_hashes[name] = sha256_bytes(text.encode("utf-8"))
    bundle_hash = sha256_bytes(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    )
    manifest = {
        "schema_version": "0.1.0",
        "canonical_uri_base": URI_BASE,
        "schema_status": "frozen",
        "file_hashes": file_hashes,
        "bundle_hash": bundle_hash,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (ROOT / "freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    readme = (
        "# Workflow Patterns — Shared Knowledge Contracts (KB-WPL-01.1)\n\n"
        f"Canonical URI base: `{URI_BASE}` (identity only — no HTTP resolution).\n\n"
        f"Bundle hash: `{bundle_hash}`\n\n"
        "WorkflowTemplate stores metadata only — no executable workflow body.\n"
        "WorkflowPattern is provider-neutral — no raw n8n JSON.\n"
    )
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    return file_hashes, bundle_hash


def main() -> None:
    _, bundle = write_bundle()
    print(f"Schemas: {len(SCHEMAS)}")
    print(f"Bundle hash: {bundle}")


if __name__ == "__main__":
    main()
