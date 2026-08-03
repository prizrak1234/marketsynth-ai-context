"""Test helpers for KB-WPL-01.1 workflow_patterns shared schemas."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
WPL_ROOT = REPO_ROOT / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
CANONICAL_URI_BASE = "https://schemas.marketsynth.ai/workflow-patterns/0.1.0/"
FROZEN_BUNDLE_HASH = "db34d8f1dbd82772d86fc921daa57d7007e748c004bf40b250023d1247823f25"

SEMANTIC_MANIFEST_KEYS = (
    "schema_version",
    "canonical_uri_base",
    "schema_status",
    "file_hashes",
    "bundle_hash",
)

FORBIDDEN_WORKFLOW_BODY_KEYS = frozenset(
    {"nodes", "connections", "workflow_body", "raw_json", "pinData", "settings"}
)
FORBIDDEN_CREDENTIAL_VALUE_KEYS = frozenset(
    {"password", "token", "api_key", "secret", "private_key", "oauth_token"}
)
FORBIDDEN_MATURITY = frozenset({"active", "executable", "approved", "deployed"})

PROV = {
    "source_type": "fixture",
    "archive_id": "arc-test",
    "content_hash": "a" * 64,
}


def load_freeze_manifest() -> dict[str, Any]:
    return json.loads((WPL_ROOT / "freeze_manifest.json").read_text(encoding="utf-8"))


def schema_registry(*, version: str = "0.1.0") -> Registry:
    root = REPO_ROOT / "packages" / "knowledge" / "workflow_patterns" / version
    if not root.is_dir():
        msg = f"unknown schema version: {version}"
        raise ValueError(msg)
    resources: list[tuple[str, Resource[Any]]] = []
    for path in sorted(root.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents)
        resources.append((path.name, resource))
        schema_id = contents.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, resource))
    return Registry().with_resources(resources)


def schema_validator(schema_name: str, *, version: str = "0.1.0") -> Draft202012Validator:
    root = REPO_ROOT / "packages" / "knowledge" / "workflow_patterns" / version
    schema = json.loads((root / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=schema_registry(version=version))


def recompute_bundle_hash() -> str:
    manifest = load_freeze_manifest()
    payload = json.dumps(manifest["file_hashes"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def semantic_manifest_subset(manifest: dict[str, Any]) -> dict[str, Any]:
    subset = {k: manifest[k] for k in SEMANTIC_MANIFEST_KEYS if k in manifest}
    subset["bundle_hash"] = recompute_bundle_hash()
    return subset


def semantic_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(semantic_manifest_subset(manifest), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def collect_schema_ids() -> list[str]:
    ids: list[str] = []
    for path in sorted(WPL_ROOT.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sid = doc.get("$id")
        if isinstance(sid, str):
            ids.append(sid)
    return ids


def remote_ref_offenders() -> list[str]:
    offenders: list[str] = []
    for path in sorted(WPL_ROOT.glob("*.schema.json")):
        text = path.read_text(encoding="utf-8")
        if re.search(r'"\$ref":\s*"https?://(?!schemas\.marketsynth\.ai)', text):
            offenders.append(path.name)
    return offenders


def unversioned_uri_offenders() -> list[str]:
    offenders: list[str] = []
    for path in sorted(WPL_ROOT.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sid = doc.get("$id", "")
        if (
            isinstance(sid, str)
            and sid.startswith("https://schemas.marketsynth.ai/workflow-patterns/")
            and "/0.1.0/" not in sid
        ):
            offenders.append(path.name)
    return offenders


def validate_workflow_template(data: dict[str, Any]) -> None:
    schema_validator("workflow-template.schema.json").validate(data)


def validate_workflow_pattern(data: dict[str, Any]) -> None:
    schema_validator("workflow-pattern.schema.json").validate(data)


def validate_practice_record(data: dict[str, Any]) -> None:
    schema_validator("practice-record.schema.json").validate(data)


def validate_manual_audit_record(data: dict[str, Any]) -> None:
    """Validate manual lineage audit record required fields (not pattern-audit-report)."""
    required = (
        "audit_id",
        "workflow_template_ids",
        "pattern_ids",
        "decision",
        "rationale",
        "owner_review_required",
    )
    for key in required:
        if key not in data:
            msg = f"manual audit missing required field: {key}"
            raise ValueError(msg)
    if data["decision"] not in {
        "approved_for_pilot",
        "approved_for_core",
        "deferred",
        "rejected",
    }:
        msg = f"invalid audit decision: {data['decision']}"
        raise ValueError(msg)


def validate_workflow_template_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in FORBIDDEN_WORKFLOW_BODY_KEYS:
        if key in data:
            errors.append(f"executable workflow body key forbidden: {key}")
    for cred in data.get("credential_references", []):
        if isinstance(cred, dict):
            for key in FORBIDDEN_CREDENTIAL_VALUE_KEYS:
                if key in cred:
                    errors.append(f"raw credential value forbidden: {key}")
    return errors


def validate_workflow_pattern_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    maturity = data.get("maturity", "")
    if maturity in FORBIDDEN_MATURITY:
        errors.append(f"forbidden maturity: {maturity}")

    for key in FORBIDDEN_WORKFLOW_BODY_KEYS:
        if key in data:
            errors.append(f"raw n8n JSON forbidden in pattern: {key}")

    text_blob = json.dumps(data)
    if '"type": "n8n-nodes-base' in text_blob or "n8n-nodes-base." in text_blob:
        errors.append("provider-specific n8n node type in provider-neutral pattern")

    approval = data.get("approval_requirements", {})
    if data.get("publication_sensitive") and not approval.get("publication_approval_required"):
        errors.append("publication pattern requires publication_approval_required")
    if data.get("billing_sensitive") and not approval.get("spend_approval_required"):
        errors.append("billing pattern requires spend_approval_required")
    if data.get("destructive") and approval.get("auto_approval_allowed"):
        errors.append("destructive pattern cannot be auto-approved")

    retry = data.get("retry_policy")
    idem = data.get("idempotency_requirements", {})
    if retry and retry not in ("none", "") and not idem.get("required"):
        errors.append("retry pattern requires idempotency policy")
    if (
        retry
        and idem.get("unknown_outcome_auto_retry")
        and idem.get("required")
        and data.get("security_class") in {"write_internal", "publication", "destructive"}
    ):
        errors.append("unknown-outcome write must not auto-retry")

    for variant in data.get("implementation_variants", []):
        if isinstance(variant, dict) and not variant.get("documented_version"):
            errors.append("provider variant missing documented_version")

    if not data.get("provenance"):
        errors.append("provenance required")
    if not data.get("tenant_scope"):
        errors.append("tenant_scope required")

    return errors


def validate_practice_semantics(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for scope in data.get("provider_version_scope", []):
        if isinstance(scope, dict) and not scope.get("documented_version"):
            errors.append("provider claim missing documented_version")
    return errors


def sample_workflow_template(**overrides: Any) -> dict[str, Any]:
    base = {
        "workflow_template_id": "wf-test-001",
        "original_name": "Test SEO Workflow",
        "normalized_name": "Test SEO Workflow",
        "source_archive_id": "arc-bots-knowledge-rar",
        "source_path_hash": "b" * 64,
        "workflow_hash": "c" * 64,
        "topology_hash": "d" * 64,
        "description": "Metadata only",
        "use_case": "SEO audit",
        "categories": ["seo"],
        "trigger_types": ["n8n-nodes-base.manualTrigger"],
        "node_types": ["n8n-nodes-base.httpRequest"],
        "providers": ["httpRequest"],
        "credential_references": [
            {"credential_type": "googleSheetsOAuth2Api", "credential_id_ref": "cred-ref-1"}
        ],
        "environment_references": [],
        "side_effects": [],
        "publication_actions": False,
        "billing_actions": False,
        "destructive_actions": False,
        "personal_data_risk": "unknown",
        "code_nodes": False,
        "shell_nodes": False,
        "database_nodes": False,
        "AI_nodes": False,
        "external_urls": [],
        "security_findings": [],
        "provider_constraints": [],
        "deprecated_components": [],
        "adaptation_status": "catalog_only",
        "quarantine_status": "quarantined",
        "tenant_scope": "global",
        "provenance": PROV,
    }
    base.update(overrides)
    return base


def sample_workflow_pattern(**overrides: Any) -> dict[str, Any]:
    base = {
        "pattern_id": "pat-human-approval-publication",
        "pattern_name": "Human Approval Before Publication",
        "pattern_category": "control_and_safety",
        "objective": "Block publication without human approval",
        "problem_context": "External publication workflows",
        "capability_ids": ["publication"],
        "related_skill_ids": ["ms.skill.n8n_workflow_architecture"],
        "input_contract": {"type": "object"},
        "output_contract": {"type": "object"},
        "steps": [
            {
                "step_id": "s1",
                "step_name": "Prepare draft",
                "step_type": "transform",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Human approval gate",
                "step_type": "approval",
                "approval_gate": "before_publication",
                "security_class": "publication",
            },
        ],
        "edges": [{"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"}],
        "required_connectors": [],
        "required_tools": [],
        "approval_requirements": {
            "human_approval_required": True,
            "approval_gates": ["before_publication"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": True,
        },
        "evidence_requirements": {"required": True, "evidence_classes": ["approval_record"]},
        "idempotency_requirements": {
            "required": True,
            "policy": "dedupe_by_event_id",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        "retry_policy": "backoff",
        "timeout_policy": "30s",
        "rate_limit_policy": "provider_default",
        "error_paths": ["human_review"],
        "rollback_or_recovery": "manual",
        "security_class": "publication",
        "tenant_scope": "global",
        "personal_data_class": "unknown",
        "publication_sensitive": True,
        "billing_sensitive": False,
        "destructive": False,
        "implementation_variants": [
            {
                "provider": "telegram",
                "documented_version": "1.0",
                "documented_at": "2026-07-23",
                "verification_status": "source_documented",
                "requires_reverification": True,
                "provenance": PROV,
            }
        ],
        "source_workflow_ids": ["wf-test-001", "wf-test-002"],
        "source_practice_ids": [],
        "known_limitations": ["Requires Connector Gateway"],
        "quality_gates": [],
        "maturity": "normalized",
        "provenance": PROV,
    }
    base.update(overrides)
    return base
