"""SKILL-01.4 — Quarantine import adapter tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from app.schemas.contracts import SkillLifecycleStatus, SkillSourceType
from app.skills.package_validator import validate_skill_package
from app.skills.quarantine_contracts import (
    QuarantineImportLimits,
    QuarantineImportOutcome,
    QuarantineImportRequest,
    QuarantineImportState,
    QuarantineSourceType,
)
from app.skills.quarantine_import import import_skill_package_to_quarantine
from app.skills.quarantine_inspection import calculate_source_fingerprint, inspect_source_tree
from app.skills.registry_contracts import SkillRegistryView
from app.skills.registry_errors import SkillRegistryRecordNotFoundError
from app.skills.registry_projection import build_registry_snapshot
from app.skills.registry_queries import derive_eligibility_view, get_skill, list_skills
from app.skills.validation_contracts import SkillValidationMode
from pydantic import ValidationError

VALID_EXTERNAL = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "skills"
    / "quarantine"
    / "valid_external"
)
FROZEN_PLATFORM = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)
FIXED_TIME = datetime(2026, 7, 23, 14, 0, 0, tzinfo=UTC)


def _request_for(path: Path, **overrides: object) -> QuarantineImportRequest:
    payload = {
        "source_path": str(path),
        "source_type": QuarantineSourceType.EXTERNAL_CANDIDATE_FIXTURE,
        "requested_by": "test-operator",
        "source_reference": "unit-test",
        "import_reason": "SKILL-01.4 regression",
        "correlation_id": "test-correlation",
    }
    payload.update(overrides)
    return QuarantineImportRequest(**payload)


def _import(
    path: Path,
    tmp_path: Path,
    *,
    state: QuarantineImportState | None = None,
    limits: QuarantineImportLimits | None = None,
    **request_overrides: object,
) -> object:
    return import_skill_package_to_quarantine(
        _request_for(path, **request_overrides),
        quarantine_base_dir=tmp_path / "quarantine",
        state=state or QuarantineImportState(),
        limits=limits,
        imported_at=FIXED_TIME,
    )


def _copy_fixture(tmp_path: Path, name: str = "pkg") -> Path:
    dest = tmp_path / name
    shutil.copytree(VALID_EXTERNAL, dest)
    return dest


def _read_manifest(root: Path) -> str:
    return (root / "manifest.yaml").read_text(encoding="utf-8")


def _write_manifest(root: Path, text: str) -> None:
    (root / "manifest.yaml").write_text(text, encoding="utf-8")


def test_01_valid_external_imports_to_quarantine(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.outcome == QuarantineImportOutcome.QUARANTINED


def test_02_effective_status_is_quarantined(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.effective_status == SkillLifecycleStatus.QUARANTINED


def test_03_source_declared_active_is_ignored(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    _write_manifest(pkg, _read_manifest(pkg).replace("status: candidate", "status: active"))
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.QUARANTINED
    assert result.provenance is not None
    assert result.provenance.source_claims["declared_status"] == "active"
    assert "declared_lifecycle_status" in result.provenance.unresolved_claims


def test_04_never_production_eligible(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.production_eligible is False


def test_05_never_tenant_visible(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.tenant_visible is False


def test_06_never_executable(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.executable is False


def test_07_audit_required_true(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.audit_required is True


def test_08_source_directory_not_mutated(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path, "source_copy")
    before = _read_manifest(pkg)
    _import(pkg, tmp_path)
    assert _read_manifest(pkg) == before


def test_09_quarantine_copy_is_isolated(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    workspace = tmp_path / "quarantine" / result.import_id / "normalized"
    assert workspace.is_dir()
    assert workspace.resolve() != VALID_EXTERNAL.resolve()


def test_10_import_result_is_immutable(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    with pytest.raises(ValidationError):
        result.outcome = QuarantineImportOutcome.REJECTED  # type: ignore[misc]


def test_11_source_fingerprint_deterministic(tmp_path: Path) -> None:
    h1 = calculate_source_fingerprint(VALID_EXTERNAL)
    h2 = calculate_source_fingerprint(VALID_EXTERNAL)
    assert h1 == h2


def test_12_materialized_hash_deterministic(tmp_path: Path) -> None:
    r1 = _import(VALID_EXTERNAL, tmp_path / "a")
    r2 = _import(VALID_EXTERNAL, tmp_path / "b")
    assert r1.materialized_package_hash == r2.materialized_package_hash


def test_13_repeated_same_source_detected(tmp_path: Path) -> None:
    state = QuarantineImportState()
    first = _import(VALID_EXTERNAL, tmp_path, state=state)
    second = _import(VALID_EXTERNAL, tmp_path, state=state)
    assert first.outcome == QuarantineImportOutcome.QUARANTINED
    assert second.outcome == QuarantineImportOutcome.CONFLICT


def test_14_same_id_version_different_hash_conflict(tmp_path: Path) -> None:
    state = QuarantineImportState()
    _import(VALID_EXTERNAL, tmp_path, state=state)
    pkg = _copy_fixture(tmp_path)
    skill_md = (pkg / "SKILL.md").read_text(encoding="utf-8") + "\n"
    (pkg / "SKILL.md").write_text(skill_md, encoding="utf-8")
    second = _import(pkg, tmp_path, state=state)
    assert second.outcome == QuarantineImportOutcome.CONFLICT


def test_15_platform_native_id_collision_conflict(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    manifest = _read_manifest(pkg).replace(
        "ms.skill.external_market_check",
        "ms.skill.market_validation",
    )
    _write_manifest(pkg, manifest)
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.CONFLICT


def test_16_expected_skill_id_mismatch_conflict(tmp_path: Path) -> None:
    result = _import(
        VALID_EXTERNAL,
        tmp_path,
        expected_skill_id="ms.skill.other",
    )
    assert result.outcome == QuarantineImportOutcome.CONFLICT


def test_17_expected_version_mismatch_conflict(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path, expected_version="9.9.9")
    assert result.outcome == QuarantineImportOutcome.CONFLICT


def test_18_symlink_source_rejected(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("Symlink creation may require elevated privileges on Windows.")
    pkg = _copy_fixture(tmp_path)
    target = pkg / "manifest.yaml"
    link = pkg / "manifest.link.yaml"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation not supported.")
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_19_symlink_escape_rejected(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("Symlink creation may require elevated privileges on Windows.")
    pkg = _copy_fixture(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    try:
        (pkg / "escape.link").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation not supported.")
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_20_executable_script_rejected(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    (pkg / "scripts").mkdir()
    (pkg / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_21_binary_executable_rejected(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    (pkg / "payload.exe").write_bytes(b"MZ")
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_22_secret_like_manifest_field_rejected(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    data = yaml.safe_load(_read_manifest(pkg))
    data["api_key"] = "evil"
    _write_manifest(pkg, yaml.safe_dump(data, sort_keys=False))
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_23_hidden_env_file_rejected(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    (pkg / ".env").write_text("SECRET=1\n", encoding="utf-8")
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_24_missing_manifest_rejected(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    (pkg / "manifest.yaml").unlink()
    result = _import(pkg, tmp_path)
    assert result.outcome in {QuarantineImportOutcome.REJECTED, QuarantineImportOutcome.INCOMPLETE}


def test_25_invalid_yaml_fails_safely(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    _write_manifest(pkg, "id: [broken\n")
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_26_network_declaration_does_not_grant_access(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    _write_manifest(pkg, _read_manifest(pkg).replace("default: deny", "default: allow"))
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_27_tool_declaration_does_not_grant_permissions(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    manifest = _read_manifest(pkg).replace(
        "allowed_tools: []",
        'allowed_tools: ["tool.x"]',
    )
    _write_manifest(pkg, manifest)
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_28_declared_approval_ignored(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    _write_manifest(pkg, _read_manifest(pkg).replace("status: candidate", "status: approved"))
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.QUARANTINED
    assert result.effective_status == SkillLifecycleStatus.QUARANTINED


def test_29_declared_tenant_scope_ignored_for_eligibility(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    version = result.registry_projection.version_record
    assert version is not None
    eligibility = derive_eligibility_view(version, tenant_id="tenant-alpha")
    assert eligibility.production_eligible is False


def test_30_provenance_separates_declared_and_verified(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.provenance is not None
    assert result.provenance.declared_author is not None
    assert result.provenance.verified_author is None
    assert result.provenance.verified_license is None


def test_31_absolute_paths_do_not_leak(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    blob = json.dumps(result.model_dump(mode="json"))
    assert "C:\\" not in blob
    assert str(VALID_EXTERNAL.resolve()) not in blob


def test_32_size_limit_enforced(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    limits = QuarantineImportLimits(max_single_file_bytes=16)
    result = _import(pkg, tmp_path, limits=limits)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_33_file_count_limit_enforced(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    limits = QuarantineImportLimits(max_file_count=2)
    result = _import(pkg, tmp_path, limits=limits)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_34_directory_depth_limit_enforced(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    deep = pkg
    for index in range(15):
        deep = deep / f"level_{index}"
        deep.mkdir()
    (deep / "leaf.txt").write_text("x", encoding="utf-8")
    limits = QuarantineImportLimits(max_directory_depth=5)
    result = _import(pkg, tmp_path, limits=limits)
    assert result.outcome == QuarantineImportOutcome.REJECTED


def test_35_static_inspection_before_validator(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    (pkg / "payload.exe").write_bytes(b"MZ")
    findings, _, _ = inspect_source_tree(pkg, limits=QuarantineImportLimits())
    assert any(item.code == "unsupported_binary" for item in findings)
    result = _import(pkg, tmp_path)
    assert result.outcome == QuarantineImportOutcome.REJECTED
    assert result.package_validation_report is None or not result.package_validation_report.valid


def test_36_validator_uses_quarantine_import_mode(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.package_validation_report is not None
    assert result.package_validation_report.validation_mode == SkillValidationMode.QUARANTINE_IMPORT


def test_37_registry_projection_remains_quarantined(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    version = result.registry_projection.version_record
    assert version is not None
    assert version.lifecycle_status == SkillLifecycleStatus.QUARANTINED
    assert version.source_type == SkillSourceType.EXTERNAL_IMPORT


def test_38_normal_tenant_queries_cannot_see_imported_record(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    version = result.registry_projection.version_record
    assert version is not None
    snapshot = build_registry_snapshot([version], generated_at=FIXED_TIME)
    with pytest.raises(SkillRegistryRecordNotFoundError):
        get_skill(
            snapshot,
            version.skill_id,
            tenant_id="tenant-alpha",
            view=SkillRegistryView.NORMAL,
        )
    assert list_skills(snapshot, tenant_id="tenant-alpha").total_count == 0


def test_39_internal_audit_query_can_inspect_metadata(tmp_path: Path) -> None:
    result = _import(VALID_EXTERNAL, tmp_path)
    version = result.registry_projection.version_record
    assert version is not None
    snapshot = build_registry_snapshot([version], generated_at=FIXED_TIME)
    record = get_skill(snapshot, version.skill_id, view=SkillRegistryView.AUDIT)
    assert record.skill_id == version.skill_id


def test_40_no_external_code_executes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_exec(*args: object, **kwargs: object) -> None:
        raise AssertionError("exec forbidden")

    monkeypatch.setattr("os.execv", _forbidden_exec)
    result = _import(VALID_EXTERNAL, tmp_path)
    assert result.outcome == QuarantineImportOutcome.QUARANTINED


def test_41_no_network_call_occurs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden_urlopen(*args: object, **kwargs: object) -> None:
        raise AssertionError("network forbidden")

    monkeypatch.setattr("urllib.request.urlopen", _forbidden_urlopen)
    with pytest.raises(ValueError):
        _request_for("https://example.com/pkg")


def test_42_cli_inspects_local_package(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "app.skills.quarantine_import", str(VALID_EXTERNAL)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "outcome: quarantined" in proc.stdout


def test_validator_quarantine_mode_allows_active_claim(tmp_path: Path) -> None:
    pkg = _copy_fixture(tmp_path)
    _write_manifest(pkg, _read_manifest(pkg).replace("status: candidate", "status: active"))
    report = validate_skill_package(pkg, mode=SkillValidationMode.QUARANTINE_IMPORT)
    assert any(w.code == "quarantine_source_status_claim_ignored" for w in report.warnings)
