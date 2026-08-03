"""KB-WPL-01.1 — Shared knowledge contract tests."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from tests.support.wpl_schema_validation import (
    CANONICAL_URI_BASE,
    FROZEN_BUNDLE_HASH,
    WPL_ROOT,
    collect_schema_ids,
    load_freeze_manifest,
    recompute_bundle_hash,
    remote_ref_offenders,
    sample_workflow_pattern,
    sample_workflow_template,
    schema_registry,
    semantic_manifest_hash,
    unversioned_uri_offenders,
    validate_practice_semantics,
    validate_workflow_pattern,
    validate_workflow_pattern_semantics,
    validate_workflow_template,
    validate_workflow_template_semantics,
)


def test_01_all_schemas_draft202012_valid() -> None:
    registry = schema_registry()
    for path in sorted(WPL_ROOT.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(doc)
        Draft202012Validator(doc, registry=registry)


def test_02_canonical_uri_versioned() -> None:
    manifest = load_freeze_manifest()
    assert manifest["canonical_uri_base"] == CANONICAL_URI_BASE
    assert CANONICAL_URI_BASE.endswith("/0.1.0/")
    assert not unversioned_uri_offenders()


def test_03_remote_refs_forbidden() -> None:
    assert remote_ref_offenders() == []


def test_04_duplicate_ids_rejected() -> None:
    ids = collect_schema_ids()
    assert len(ids) == len(set(ids))


def test_05_unknown_versions_rejected() -> None:
    with pytest.raises(ValueError, match="unknown schema version"):
        schema_registry(version="9.9.9")


def test_06_workflow_template_fixture_valid() -> None:
    validate_workflow_template(sample_workflow_template())


def test_07_workflow_pattern_fixture_valid() -> None:
    validate_workflow_pattern(sample_workflow_pattern())


def test_08_raw_workflow_body_rejected() -> None:
    bad = sample_workflow_template(nodes=[{"type": "code"}])
    errors = validate_workflow_template_semantics(bad)
    assert any("nodes" in e for e in errors)


def test_09_raw_credential_value_rejected() -> None:
    bad = sample_workflow_template(
        credential_references=[
            {"credential_type": "x", "credential_id_ref": "1", "token": "secret"},
        ],
    )
    errors = validate_workflow_template_semantics(bad)
    assert any("token" in e for e in errors)


def test_10_credential_reference_allowed() -> None:
    data = sample_workflow_template()
    validate_workflow_template(data)
    assert not validate_workflow_template_semantics(data)


def test_11_active_maturity_rejected() -> None:
    bad = sample_workflow_pattern(maturity="active")
    errors = validate_workflow_pattern_semantics(bad)
    assert any("active" in e for e in errors)


def test_12_provider_claim_without_version_scope_rejected() -> None:
    practice = {
        "practice_id": "p1",
        "title": "T",
        "domain": "n8n",
        "problem": "P",
        "recommended_practice": "R",
        "provider_version_scope": [
            {
                "provider": "telegram",
                "documented_at": "2026-07-23",
                "verification_status": "claimed",
                "requires_reverification": True,
                "provenance": {"source_type": "f", "archive_id": "a"},
            }
        ],
        "verification_status": "claimed",
        "tenant_scope": "global",
        "provenance": {"source_type": "f", "archive_id": "a"},
    }
    errors = validate_practice_semantics(practice)
    assert any("documented_version" in e for e in errors)


def test_13_publication_pattern_without_approval_rejected() -> None:
    bad = deepcopy(sample_workflow_pattern())
    bad["approval_requirements"]["publication_approval_required"] = False
    errors = validate_workflow_pattern_semantics(bad)
    assert any("publication_approval_required" in e for e in errors)


def test_14_retry_pattern_without_idempotency_rejected() -> None:
    bad = deepcopy(sample_workflow_pattern())
    bad["idempotency_requirements"]["required"] = False
    errors = validate_workflow_pattern_semantics(bad)
    assert any("idempotency" in e for e in errors)


def test_15_destructive_pattern_cannot_be_auto_approved() -> None:
    bad = sample_workflow_pattern(
        destructive=True,
        security_class="destructive",
        approval_requirements={
            "human_approval_required": True,
            "approval_gates": ["before_destructive_action"],
            "auto_approval_allowed": True,
            "spend_approval_required": False,
            "publication_approval_required": False,
        },
        publication_sensitive=False,
    )
    errors = validate_workflow_pattern_semantics(bad)
    assert any("auto-approved" in e for e in errors)


def test_16_provenance_required_on_pattern() -> None:
    bad = sample_workflow_pattern()
    del bad["provenance"]
    with pytest.raises(ValidationError):
        validate_workflow_pattern(bad)


def test_17_tenant_scope_validation() -> None:
    bad = sample_workflow_pattern(tenant_scope="")
    errors = validate_workflow_pattern_semantics(bad)
    assert any("tenant_scope" in e for e in errors)


def test_18_schema_hashes_deterministic() -> None:
    m1 = load_freeze_manifest()
    m2 = load_freeze_manifest()
    assert m1["file_hashes"] == m2["file_hashes"]


def test_19_bundle_hash_deterministic() -> None:
    manifest = load_freeze_manifest()
    assert recompute_bundle_hash() == manifest["bundle_hash"]
    assert manifest["bundle_hash"] == FROZEN_BUNDLE_HASH


def test_20_timestamp_excluded_from_semantic_hash() -> None:
    m1 = load_freeze_manifest()
    h1 = semantic_manifest_hash(m1)
    m2 = deepcopy(m1)
    m2["generated_at"] = "2099-01-01T00:00:00Z"
    h2 = semantic_manifest_hash(m2)
    assert h1 == h2


def test_21_workflow_template_no_active_adaptation_status() -> None:
    schema = json.loads((WPL_ROOT / "workflow-template.schema.json").read_text(encoding="utf-8"))
    enum = set(schema["properties"]["adaptation_status"]["enum"])
    assert "active" not in enum


def test_22_all_schema_files_present() -> None:
    expected = {
        "knowledge-artifact.schema.json",
        "source-reference.schema.json",
        "workflow-template.schema.json",
        "workflow-pattern.schema.json",
        "workflow-pattern-step.schema.json",
        "workflow-pattern-edge.schema.json",
        "capability-reference.schema.json",
        "connector-requirement.schema.json",
        "tool-requirement.schema.json",
        "practice-record.schema.json",
        "error-pattern.schema.json",
        "quality-gate.schema.json",
        "security-finding.schema.json",
        "provider-constraint.schema.json",
        "provenance.schema.json",
        "pattern-audit-report.schema.json",
    }
    present = {p.name for p in WPL_ROOT.glob("*.schema.json")}
    assert expected == present
