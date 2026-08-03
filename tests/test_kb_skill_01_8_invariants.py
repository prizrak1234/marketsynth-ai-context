"""KB-SKILL-01.8 — Integrated freeze audit invariant tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.knowledge.linking.analyzer import ArtifactRef, analyze_links
from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import expected_frozen_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.kb_skill_validation import (
    FROZEN_CIM_BUNDLE_HASH,
    FROZEN_MARKETING_CLAIMS_HASH,
    FROZEN_MV_020_HASH,
    FROZEN_POSITIONING_HASH,
    KB_SKILL_PACKAGE_HASHES,
    load_external_artifacts_manifest,
    load_workflow_catalog,
    recompute_external_artifacts_bundle_hash,
)
from tests.support.marketing_claims_validation import load_freeze_manifest as load_mc_manifest

REPO = Path(__file__).resolve().parents[1]
AUDIT_DOC = REPO / "docs/rfc/KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md"

KB_SKILLS = tuple(KB_SKILL_PACKAGE_HASHES.keys())


def test_01_audit_document_exists() -> None:
    assert AUDIT_DOC.is_file()


def test_02_frozen_positioning_and_mv_unchanged() -> None:
    assert expected_frozen_package_hash("ms.skill.positioning", "0.1.0") == FROZEN_POSITIONING_HASH
    assert expected_frozen_package_hash("ms.skill.market_validation", "0.2.0") == FROZEN_MV_020_HASH


def test_03_cim_and_marketing_claims_bundles_unchanged() -> None:
    cim = json.loads(
        (REPO / "packages/knowledge/customer_intelligence/0.1.0/freeze_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert cim["bundle_hash"] == FROZEN_CIM_BUNDLE_HASH
    assert load_mc_manifest()["bundle_hash"] == FROZEN_MARKETING_CLAIMS_HASH


def test_04_external_artifacts_bundle_deterministic() -> None:
    manifest = load_external_artifacts_manifest()
    assert recompute_external_artifacts_bundle_hash() == manifest["bundle_hash"]


def test_05_all_kb_skills_validate_and_non_production() -> None:
    for skill_id in KB_SKILLS:
        root = REPO / "packages" / "skills" / skill_id
        report = validate_skill_package(root)
        assert report.valid is True
        projection = project_validation_report(report)
        assert derive_eligibility_view(projection.version_record).production_eligible is False


def test_06_kb_skill_package_hashes() -> None:
    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected


def test_07_workflow_catalog_quarantine_only() -> None:
    catalog = load_workflow_catalog()
    allowed_adaptation = {"catalog_only", "reusable_pattern_candidate", "requires_rewrite"}
    for template in catalog["templates"]:
        assert template["adaptation_status"] in allowed_adaptation
        assert template["quarantine_status"] == "quarantined"


def test_08_workflow_catalog_no_node_bodies() -> None:
    catalog = load_workflow_catalog()
    for template in catalog["templates"][:20]:
        assert "nodes" not in template
        assert "connections" not in template


def test_09_knowledge_links_no_cross_tenant() -> None:
    artifacts = [
        ArtifactRef("a1", "Doc A", tenant_scope="tenant-a"),
        ArtifactRef(
            "a2",
            "Doc B",
            tenant_scope="tenant-b",
            existing_links=[{"target_artifact_id": "a1", "relation": "related_to"}],
        ),
    ]
    result = analyze_links(artifacts, tenant_id="tenant-b")
    assert result.cross_tenant_link_rejections


def test_10_orphan_detection() -> None:
    artifacts = [
        ArtifactRef("a1", "Root"),
        ArtifactRef("a2", "Child", existing_links=[{"target_artifact_id": "a1"}]),
    ]
    result = analyze_links(artifacts)
    assert "a2" in result.orphan_artifacts
    assert "a1" not in result.orphan_artifacts


def test_11_presentation_skill_non_executable_manifest() -> None:
    manifest_path = REPO / "packages/skills/ms.skill.presentation_architecture/manifest.yaml"
    manifest = manifest_path.read_text(encoding="utf-8")
    assert "executable: false" in manifest
    assert "network_policy" in manifest


def test_12_n8n_skills_no_deployment_permissions() -> None:
    for skill_id in (
        "ms.skill.n8n_workflow_architecture",
        "ms.skill.n8n_workflow_debugging",
        "ms.skill.n8n_deployment_review",
    ):
        manifest_path = REPO / "packages/skills" / skill_id / "manifest.yaml"
        manifest = manifest_path.read_text(encoding="utf-8")
        assert "allowed_tools:[]" in manifest.replace(" ", "")
