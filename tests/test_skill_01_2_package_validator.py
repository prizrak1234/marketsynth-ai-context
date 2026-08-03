"""SKILL-01.2 — Production manifest and package validator tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from app.schemas.contracts import SkillLifecycleStatus, SkillManifest
from app.skills.errors import SkillManifestParseError
from app.skills.hashing import calculate_skill_package_hash
from app.skills.manifest_parser import parse_manifest_bytes, parse_skill_manifest
from app.skills.package_validator import validate_skill_package

FROZEN_PACKAGE = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)
FROZEN_HASH = "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
FIXTURE_MANIFEST = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "skill_manifests"
    / "ms.skill.market_validation.v0.1.0.json"
)


def _copy_package(tmp_path: Path) -> Path:
    dest = tmp_path / "pkg"
    shutil.copytree(FROZEN_PACKAGE, dest)
    return dest


def _read_manifest(root: Path) -> str:
    return (root / "manifest.yaml").read_text(encoding="utf-8")


def _write_manifest(root: Path, text: str) -> None:
    (root / "manifest.yaml").write_text(text, encoding="utf-8")


def test_01_frozen_package_passes_production_validation() -> None:
    report = validate_skill_package(FROZEN_PACKAGE)
    assert report.valid is True
    assert report.skill_id == "ms.skill.market_validation"
    assert report.status == SkillLifecycleStatus.CANDIDATE


def test_02_parsed_manifest_matches_domain_contract() -> None:
    manifest = parse_skill_manifest(FROZEN_PACKAGE / "manifest.yaml")
    fixture_data = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    expected = SkillManifest.model_validate(fixture_data)
    assert manifest.id == expected.id
    assert manifest.version == expected.version
    assert manifest.status == expected.status
    assert manifest.required_inputs.schema_ref == expected.required_inputs.schema_ref
    assert manifest.output_schema.schema_ref == expected.output_schema.schema_ref
    assert manifest.permissions_deny_by_default() == expected.permissions_deny_by_default()


def test_03_normalized_snapshot_stable() -> None:
    manifest = parse_skill_manifest(FROZEN_PACKAGE / "manifest.yaml")
    first = manifest.normalized_registry_snapshot()
    second = SkillManifest.model_validate(first).normalized_registry_snapshot()
    assert first == second


def test_04_package_hash_deterministic() -> None:
    h1 = calculate_skill_package_hash(FROZEN_PACKAGE)
    h2 = calculate_skill_package_hash(FROZEN_PACKAGE)
    assert h1 == h2 == FROZEN_HASH


def test_05_hash_changes_when_content_changes(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    before = calculate_skill_package_hash(pkg)
    (pkg / "resources" / "README.md").write_text("changed\n", encoding="utf-8")
    after = calculate_skill_package_hash(pkg)
    assert before != after


def test_06_file_ordering_does_not_change_hash(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    h1 = calculate_skill_package_hash(pkg)
    # Touch files in reverse order — hash algorithm sorts paths lexicographically.
    files = sorted(pkg.rglob("*"))
    for path in reversed(files):
        if path.is_file():
            path.write_bytes(path.read_bytes())
    h2 = calculate_skill_package_hash(pkg)
    assert h1 == h2


def test_07_missing_manifest_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    (pkg / "manifest.yaml").unlink()
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "skill_manifest_missing" for err in report.errors)


def test_08_invalid_yaml_fails_safely(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    _write_manifest(pkg, "id: [unclosed\n")
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(
        "yaml" in err.message.lower() or err.code == "skill_manifest_parse_error"
        for err in report.errors
    )


def test_09_multiple_yaml_documents_fail(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    _write_manifest(pkg, _read_manifest(pkg) + "\n---\nfoo: bar\n")
    with pytest.raises(SkillManifestParseError):
        parse_manifest_bytes((pkg / "manifest.yaml").read_bytes())


def test_10_duplicate_yaml_keys_fail(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    _write_manifest(pkg, "id: ms.skill.market_validation\nid: duplicate\n")
    with pytest.raises(SkillManifestParseError, match="Duplicate"):
        parse_manifest_bytes((pkg / "manifest.yaml").read_bytes())


def test_11_custom_yaml_tags_fail(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    _write_manifest(pkg, "!!python/object: __main__.Evil {}\n")
    with pytest.raises(SkillManifestParseError):
        parse_manifest_bytes((pkg / "manifest.yaml").read_bytes())


def test_12_yaml_coercion_status_yes_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("status: candidate", "status: yes")
    _write_manifest(pkg, text)
    with pytest.raises(SkillManifestParseError, match="status"):
        parse_manifest_bytes((pkg / "manifest.yaml").read_bytes())


def test_13_unknown_status_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("status: candidate", "status: imaginary")
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_14_paused_status_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("status: candidate", "status: paused")
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_15_active_status_fails_candidate_validation(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("status: candidate", "status: active")
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "lifecycle_status_not_candidate" for err in report.errors)


def test_16_secret_like_manifest_key_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    data = yaml.safe_load(_read_manifest(pkg))
    data["api_key"] = "evil"
    _write_manifest(pkg, yaml.safe_dump(data, sort_keys=False))
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "security_forbidden_manifest_key" for err in report.errors)


def test_17_nonempty_allowed_tools_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("allowed_tools: []", 'allowed_tools: ["connector.tool"]')
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "security_allowed_tools_nonempty" for err in report.errors)


def test_18_network_allow_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("default: deny", "default: allow")
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "security_network_not_deny" for err in report.errors)


def test_19_scripts_enabled_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace("enabled: false", "enabled: true")
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "security_scripts_enabled" for err in report.errors)


def test_20_executable_script_file_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    evil = pkg / "scripts"
    evil.mkdir()
    (evil / "run.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "security_executable_file" for err in report.errors)


def test_21_absolute_schema_path_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace(
        "schema_ref: schemas/input.schema.json",
        "schema_ref: /etc/passwd",
    )
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "skill_schema_missing" for err in report.errors)


def test_22_traversal_schema_path_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    text = _read_manifest(pkg).replace(
        "schema_ref: schemas/input.schema.json",
        "schema_ref: ../outside.json",
    )
    _write_manifest(pkg, text)
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_23_escaping_symlink_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name == "nt":
        pytest.skip("Symlink creation may require elevated privileges on Windows.")
    pkg = _copy_package(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = pkg / "link.out"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation not supported in this environment.")
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "security_symlink_forbidden" for err in report.errors)


def test_24_missing_input_schema_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    (pkg / "schemas" / "input.schema.json").unlink()
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "skill_schema_missing" for err in report.errors)


def test_25_missing_output_schema_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    (pkg / "schemas" / "output.schema.json").unlink()
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_26_invalid_json_schema_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    (pkg / "schemas" / "input.schema.json").write_text("{not json", encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any(err.code == "skill_schema_invalid" for err in report.errors)


def test_27_invalid_json_schema_meta_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    schema = json.loads((pkg / "schemas" / "output.schema.json").read_text(encoding="utf-8"))
    schema["type"] = "not-a-valid-type"
    (pkg / "schemas" / "output.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_28_remote_ref_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    schema = json.loads((pkg / "schemas" / "input.schema.json").read_text(encoding="utf-8"))
    schema["$ref"] = "https://example.com/evil.schema.json"
    (pkg / "schemas" / "input.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False
    assert any("Remote" in err.message for err in report.errors)


def test_29_output_schema_missing_lineage_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    schema = json.loads((pkg / "schemas" / "output.schema.json").read_text(encoding="utf-8"))
    schema["required"] = [field for field in schema["required"] if field != "skill_id"]
    (pkg / "schemas" / "output.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_30_output_schema_unknown_verdict_fails(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    schema = json.loads((pkg / "schemas" / "output.schema.json").read_text(encoding="utf-8"))
    schema["properties"]["verdict"]["enum"] = ["proceed", "totally_made_up"]
    (pkg / "schemas" / "output.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    report = validate_skill_package(pkg)
    assert report.valid is False


def test_31_safe_error_messages_contain_no_secret_values(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    data = yaml.safe_load(_read_manifest(pkg))
    data["client_secret"] = "super-secret-value-12345"
    _write_manifest(pkg, yaml.safe_dump(data, sort_keys=False))
    report = validate_skill_package(pkg)
    blob = json.dumps(report.model_dump(mode="json"))
    assert "super-secret-value-12345" not in blob


def test_32_cli_returns_zero_for_valid_package() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "app.skills.validate_package", str(FROZEN_PACKAGE)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "valid: True" in proc.stdout


def test_33_cli_returns_nonzero_for_invalid_package(tmp_path: Path) -> None:
    pkg = _copy_package(tmp_path)
    (pkg / "manifest.yaml").unlink()
    proc = subprocess.run(
        [sys.executable, "-m", "app.skills.validate_package", str(pkg)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_34_no_runtime_execution_during_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pkg = _copy_package(tmp_path)

    def _forbidden_exec(*args: object, **kwargs: object) -> None:
        raise AssertionError("exec must not run during package validation")

    def _forbidden_subprocess(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess")

    monkeypatch.setattr("os.execv", _forbidden_exec)
    monkeypatch.setattr("subprocess.run", _forbidden_subprocess)
    report = validate_skill_package(pkg)
    assert report.valid is True


def test_35_production_hash_in_validation_report() -> None:
    report = validate_skill_package(FROZEN_PACKAGE)
    assert report.package_hash == FROZEN_HASH
