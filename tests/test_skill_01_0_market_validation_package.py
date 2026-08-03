"""SKILL-01.0 — Market Validation driver skeleton package tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.support.skill_package_validation import (
    MarketValidationVerdict,
    PACKAGE_ROOT,
    SKILL_01_0_ALLOWED_STATUSES,
    load_json_fixture,
    manifest_contains_required_keys,
    no_secrets_in_manifest,
    package_paths_safe,
    package_structure_valid,
    parse_manifest_scalar,
    read_manifest_text,
    scripts_disabled,
    validate_input_fixture,
    validate_output_fixture,
)

MANIFEST = read_manifest_text()


def test_01_package_structure_is_valid() -> None:
    assert package_structure_valid()


def test_02_manifest_contains_all_required_fields() -> None:
    missing = manifest_contains_required_keys(MANIFEST)
    assert missing == []


def test_03_id_and_version_are_valid() -> None:
    assert parse_manifest_scalar(MANIFEST, "id") == "ms.skill.market_validation"
    assert parse_manifest_scalar(MANIFEST, "version") == "0.1.0"


def test_04_released_identity_fields_are_deterministic() -> None:
    assert parse_manifest_scalar(MANIFEST, "name") == "Market Validation"
    assert parse_manifest_scalar(MANIFEST, "owner") == "Marketsynth Platform"
    assert parse_manifest_scalar(MANIFEST, "source") == "platform_native"


def test_05_status_is_allowed() -> None:
    status = parse_manifest_scalar(MANIFEST, "status")
    assert status in SKILL_01_0_ALLOWED_STATUSES


def test_06_no_paused_status_exists() -> None:
    assert "paused" not in MANIFEST.lower()
    assert "status: paused" not in MANIFEST


def test_07_no_secrets_or_credential_fields_in_manifest() -> None:
    assert no_secrets_in_manifest(MANIFEST)


def test_08_no_undeclared_scripts_directory() -> None:
    scripts_dir = PACKAGE_ROOT / "scripts"
    assert not scripts_dir.exists()


def test_09_scripts_are_disabled_in_manifest() -> None:
    assert scripts_disabled(MANIFEST)


def test_10_no_path_traversal_in_package_paths() -> None:
    assert package_paths_safe()


def test_11_input_schema_validates_complete_example() -> None:
    data = load_json_fixture("tests/fixtures/input_complete.json")
    parsed = validate_input_fixture(data)
    assert "meal kits" in parsed.idea_description


def test_12_input_schema_accepts_explicitly_allowed_partial_input() -> None:
    data = load_json_fixture("tests/fixtures/input_incomplete.json")
    parsed = validate_input_fixture(data)
    assert parsed.target_market is None
    assert parsed.field_states is not None


@pytest.mark.parametrize(
    "fixture_path",
    [
        "tests/fixtures/output_proceed_with_conditions.json",
        "tests/fixtures/output_insufficient_evidence.json",
    ],
)
def test_13_output_schema_validates_allowed_verdicts(fixture_path: str) -> None:
    data = load_json_fixture(fixture_path)
    parsed = validate_output_fixture(data)
    assert parsed.verdict in MarketValidationVerdict


def test_14_output_schema_rejects_unknown_verdict_values() -> None:
    data = load_json_fixture("tests/fixtures/output_invalid_verdict.json")
    with pytest.raises(ValidationError):
        validate_output_fixture(data)


def test_15_evidence_fields_required_in_output_fixtures() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_with_conditions.json")
    parsed = validate_output_fixture(data)
    assert parsed.supporting_evidence
    assert parsed.evidence_gaps
    assert parsed.provenance.skill_id == "ms.skill.market_validation"


def test_16_skill_id_and_skill_version_appear_in_output() -> None:
    data = load_json_fixture("tests/fixtures/output_insufficient_evidence.json")
    parsed = validate_output_fixture(data)
    assert parsed.skill_id == "ms.skill.market_validation"
    assert parsed.skill_version == "0.1.0"


def test_17_approval_policy_cannot_be_omitted_from_manifest() -> None:
    assert "approval_policy:" in MANIFEST
    assert "launch_or_execution_transition:" in MANIFEST


def test_18_tenant_scope_is_global_platform_owned() -> None:
    assert parse_manifest_scalar(MANIFEST, "tenant_scope") == "global"


def test_19_no_connector_or_tool_permission_granted() -> None:
    assert "allowed_tools: []" in MANIFEST
    assert "network_policy:" in MANIFEST
    assert "default: deny" in MANIFEST


def test_20_package_cannot_be_marked_active_in_skeleton_manifest() -> None:
    assert parse_manifest_scalar(MANIFEST, "status") != "active"
    invalid = read_manifest_text(PACKAGE_ROOT / "tests/fixtures/manifest_active_status.yaml")
    assert parse_manifest_scalar(invalid, "status") == "active"
    assert parse_manifest_scalar(MANIFEST, "status") == "candidate"


def test_invalid_manifest_with_secret_fails_secret_scan() -> None:
    invalid = read_manifest_text(PACKAGE_ROOT / "tests/fixtures/manifest_with_secret.yaml")
    assert not no_secrets_in_manifest(invalid)


def test_skill_md_exists_and_is_instruction_only() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Evidence discipline" in skill_md
    assert "api_key" not in skill_md.lower()
    assert "allowed_tools" not in skill_md


def test_no_scripts_executable_under_package() -> None:
    for path in PACKAGE_ROOT.rglob("*"):
        if path.suffix == ".py" and path.is_file():
            pytest.fail(f"Unexpected executable script in package: {path.relative_to(PACKAGE_ROOT)}")
