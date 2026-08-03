"""SKILL-01.1 — Canonical Skill package domain contracts."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.contracts import (
    SkillLifecycleStatus,
    SkillManifest,
    SkillPackageDescriptor,
    SkillSourceType,
    SkillTenantScope,
    SkillValidationVerdict,
    skill_lifecycle_forbids_paused,
    skill_lifecycle_transition_allowed,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "skill_manifests"
    / "ms.skill.market_validation.v0.1.0.json"
)

FROZEN_HASH = "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"


def _load_manifest_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_lifecycle_has_no_paused_status() -> None:
    assert skill_lifecycle_forbids_paused()
    assert not hasattr(SkillLifecycleStatus, "PAUSED")


def test_lifecycle_transitions_candidate_to_quarantined() -> None:
    assert skill_lifecycle_transition_allowed(
        SkillLifecycleStatus.CANDIDATE,
        SkillLifecycleStatus.QUARANTINED,
    )


def test_lifecycle_rejects_quarantined_to_active() -> None:
    assert not skill_lifecycle_transition_allowed(
        SkillLifecycleStatus.QUARANTINED,
        SkillLifecycleStatus.ACTIVE,
    )


def test_manifest_roundtrip_from_fixture() -> None:
    raw = _load_manifest_fixture()
    manifest = SkillManifest.model_validate(raw)
    snapshot = manifest.normalized_registry_snapshot()
    assert snapshot["id"] == "ms.skill.market_validation"
    assert snapshot["version"] == "0.1.0"
    assert snapshot["status"] == "candidate"
    assert snapshot["allowed_tools"] == []
    assert snapshot["network_policy"]["default"] == "deny"
    assert snapshot["script_policy"]["enabled"] is False


def test_manifest_roundtrip_reparse_normalized() -> None:
    manifest = SkillManifest.model_validate(_load_manifest_fixture())
    normalized = manifest.normalized_registry_snapshot()
    again = SkillManifest.model_validate(normalized)
    assert again.normalized_registry_snapshot() == normalized


def test_package_descriptor_from_manifest() -> None:
    manifest = SkillManifest.model_validate(_load_manifest_fixture())
    descriptor = SkillPackageDescriptor(
        skill_id=manifest.id,
        version=manifest.version,
        status=manifest.status,
        package_root="packages/skills/ms.skill.market_validation",
        content_hash_sha256=FROZEN_HASH,
        manifest=manifest,
    )
    assert descriptor.skill_id == "ms.skill.market_validation"
    assert descriptor.manifest.source == SkillSourceType.PLATFORM_NATIVE


def test_manifest_rejects_active_status_in_skeleton() -> None:
    raw = _load_manifest_fixture()
    raw["status"] = "active"
    manifest = SkillManifest.model_validate(raw)
    assert not manifest.is_non_active_skeleton()


def test_manifest_rejects_invalid_skill_id() -> None:
    raw = _load_manifest_fixture()
    raw["id"] = "invalid-id"
    with pytest.raises(ValidationError):
        SkillManifest.model_validate(raw)


def test_manifest_rejects_non_empty_allowed_tools_by_default_policy() -> None:
    raw = _load_manifest_fixture()
    raw["allowed_tools"] = ["firecrawl.scrape"]
    manifest = SkillManifest.model_validate(raw)
    assert not manifest.permissions_deny_by_default()


def test_provenance_audit_research_id_not_production_skill_id() -> None:
    manifest = SkillManifest.model_validate(_load_manifest_fixture())
    assert manifest.provenance.audit_research_id == "MS-SKILL-005"
    assert manifest.id != "MS-SKILL-005"


def test_validation_verdict_enum_covers_package_schema() -> None:
    expected = {
        "proceed",
        "proceed_with_conditions",
        "revise",
        "defer",
        "stop",
        "insufficient_evidence",
    }
    assert {v.value for v in SkillValidationVerdict} == expected


def test_tenant_scope_global_for_driver_package() -> None:
    manifest = SkillManifest.model_validate(_load_manifest_fixture())
    assert manifest.tenant_scope == SkillTenantScope.GLOBAL


def test_dependencies_use_declared_future_only() -> None:
    manifest = SkillManifest.model_validate(_load_manifest_fixture())
    assert len(manifest.dependencies.declared_future_dependencies) == 4
    ids = {d.id for d in manifest.dependencies.declared_future_dependencies}
    assert "ms.skill.market_research" in ids


def test_manifest_field_mapping_required_inputs_and_output_schema() -> None:
    manifest = SkillManifest.model_validate(_load_manifest_fixture())
    assert manifest.required_inputs.schema_ref == "schemas/input.schema.json"
    assert manifest.output_schema.schema_ref == "schemas/output.schema.json"


def test_normalized_snapshot_stable_after_copy() -> None:
    raw = deepcopy(_load_manifest_fixture())
    first = SkillManifest.model_validate(raw).normalized_registry_snapshot()
    second = SkillManifest.model_validate(raw).normalized_registry_snapshot()
    assert first == second
