"""KB-SKILL-01.1 — External artifact shared contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from tests.support.kb_skill_validation import (
    load_external_artifacts_manifest,
    recompute_external_artifacts_bundle_hash,
)

REPO = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO / "packages" / "knowledge" / "external_artifacts" / "0.1.0"

REQUIRED_SCHEMAS = (
    "knowledge-artifact.schema.json",
    "source-reference.schema.json",
    "methodology-record.schema.json",
    "practice-record.schema.json",
    "error-pattern.schema.json",
    "workflow-template.schema.json",
    "workflow-node-reference.schema.json",
    "dependency-reference.schema.json",
    "security-finding.schema.json",
    "quality-gate.schema.json",
    "knowledge-link.schema.json",
    "provenance.schema.json",
    "import-report.schema.json",
)


def test_01_all_schemas_present() -> None:
    for name in REQUIRED_SCHEMAS:
        assert (SCHEMA_ROOT / name).is_file()


def test_02_canonical_uri_base() -> None:
    manifest = load_external_artifacts_manifest()
    assert manifest["canonical_uri_base"] == (
        "https://schemas.marketsynth.ai/external-artifacts/0.1.0/"
    )


def test_03_bundle_hash_deterministic() -> None:
    manifest = load_external_artifacts_manifest()
    assert recompute_external_artifacts_bundle_hash() == manifest["bundle_hash"]


def test_04_workflow_template_no_active_status() -> None:
    schema = json.loads((SCHEMA_ROOT / "workflow-template.schema.json").read_text(encoding="utf-8"))
    enum = schema["properties"]["adaptation_status"]["enum"]
    assert "active" not in enum


def test_05_knowledge_artifact_trust_statuses() -> None:
    path = SCHEMA_ROOT / "knowledge-artifact.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(schema["properties"]["trust_status"]["enum"])
    assert "quarantined" in allowed
    assert "rejected" in allowed


def test_06_practice_record_verification_not_auto_reproduced() -> None:
    schema = json.loads((SCHEMA_ROOT / "practice-record.schema.json").read_text(encoding="utf-8"))
    statuses = schema["properties"]["verification_status"]["enum"]
    assert "reproduced" in statuses
    assert "claimed" in statuses
