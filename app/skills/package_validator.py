"""Production Skill package validator (SKILL-01.2)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError

from app.schemas.contracts import (
    SkillLifecycleStatus,
    SkillManifest,
    SkillNetworkPolicyDefault,
    SkillOutputContractType,
    SkillSourceType,
)
from app.skills.errors import (
    SkillPackageNotFoundError,
    SkillValidationError,
)
from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import (
    frozen_package_hash_conflict,
    resolve_output_contract_type,
)
from app.skills.manifest_parser import parse_manifest_bytes, parse_skill_manifest
from app.skills.output_contract_rules import validate_output_contract_schema
from app.skills.validation_contracts import (
    VALIDATOR_VERSION,
    SkillPackageValidationReport,
    SkillSchemaValidationResult,
    SkillValidationMode,
)

MANIFEST_FILENAME = "manifest.yaml"
SKILL_MD_FILENAME = "SKILL.md"
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

EXECUTABLE_SUFFIXES = frozenset(
    {".sh", ".bash", ".py", ".pyc", ".exe", ".bat", ".cmd", ".ps1", ".pl", ".rb"}
)

FORBIDDEN_MANIFEST_KEY_FRAGMENTS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "token",
        "password",
        "credential",
        "authorization",
        "private_key",
        "access_key",
        "refresh_token",
        "client_secret",
    }
)

SKILL_MD_FORBIDDEN_PATTERNS = re.compile(
    r"(allowed_tools\s*:|network_policy\s*:|script_policy\s*:|api_key\s*:|credential_binding)",
    re.IGNORECASE,
)

CANDIDATE_ALLOWED_STATUSES = frozenset(
    {SkillLifecycleStatus.CANDIDATE, SkillLifecycleStatus.QUARANTINED}
)

QUARANTINE_IGNORED_STATUSES = frozenset(
    {
        SkillLifecycleStatus.ACTIVE,
        SkillLifecycleStatus.APPROVED,
        SkillLifecycleStatus.AUDITED,
    }
)


def _apply_quarantine_import_rules(
    report: SkillPackageValidationReport,
    manifest: SkillManifest,
) -> None:
    """External import validation — untrusted source, effective quarantine overlay elsewhere."""
    if manifest.status in QUARANTINE_IGNORED_STATUSES:
        report.add_warning(
            code="quarantine_source_status_claim_ignored",
            message=(
                f"Source-declared status '{manifest.status.value}' is recorded as a claim only; "
                "effective import status is quarantined."
            ),
            location="status",
            rule_reference="RFC-SKILL-003",
        )
    if manifest.allowed_tools:
        report.add_error(
            code="quarantine_declared_tools_forbidden",
            message="Declared allowed_tools cannot grant permissions during quarantine import.",
            location="allowed_tools",
            rule_reference="RFC-SKILL-003",
        )
    if manifest.network_policy.default != SkillNetworkPolicyDefault.DENY:
        report.add_error(
            code="quarantine_declared_network_forbidden",
            message="Declared network access cannot grant permissions during quarantine import.",
            location="network_policy.default",
            rule_reference="RFC-SKILL-003",
        )
    if manifest.script_policy.enabled:
        report.add_error(
            code="quarantine_scripts_enabled",
            message="Scripts remain prohibited during quarantine import.",
            location="script_policy.enabled",
            rule_reference="RFC-SKILL-003",
        )
    if manifest.activation_conditions.executable:
        report.add_error(
            code="quarantine_executable_flag",
            message="Executable activation cannot be granted during quarantine import.",
            location="activation_conditions.executable",
            rule_reference="RFC-SKILL-003",
        )
    if manifest.source == SkillSourceType.PLATFORM_NATIVE:
        report.add_warning(
            code="quarantine_untrusted_source_type_claim",
            message=(
                "Source declares platform_native; external import treats this as "
                "an untrusted claim."
            ),
            location="source",
            rule_reference="RFC-SKILL-003",
        )


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _resolve_package_root(package_path: Path) -> Path:
    root = package_path.resolve()
    if not root.is_dir():
        raise SkillPackageNotFoundError("Skill package directory was not found.")
    return root


def _resolve_in_package(root: Path, ref: str) -> Path | None:
    if not ref or ref.startswith(("/", "\\")):
        return None
    parts = Path(ref).parts
    if ".." in parts:
        return None
    target = (root / ref).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    return target


def _collect_forbidden_manifest_keys(data: Any, prefix: str = "") -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            location = f"{prefix}.{key}" if prefix else key
            normalized = _normalize_key(str(key))
            for fragment in FORBIDDEN_MANIFEST_KEY_FRAGMENTS:
                if fragment in normalized:
                    findings.append((location, str(key)))
                    break
            findings.extend(_collect_forbidden_manifest_keys(value, location))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            findings.extend(_collect_forbidden_manifest_keys(item, f"{prefix}[{index}]"))
    return findings


def _walk_schema_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str):
                refs.append(item)
            refs.extend(_walk_schema_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_walk_schema_refs(item))
    return refs


def _validate_json_schema_file(
    *,
    root: Path,
    schema_ref: str,
    is_output: bool,
    output_contract_type: SkillOutputContractType | None = None,
) -> SkillSchemaValidationResult:
    result = SkillSchemaValidationResult(schema_ref=schema_ref, valid=False)
    target = _resolve_in_package(root, schema_ref)
    if target is None or not target.is_file():
        result.errors.append("Referenced schema path is missing or unsafe.")
        return result

    try:
        schema = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"Invalid JSON: {exc.msg}")
        return result

    if not isinstance(schema, dict):
        result.errors.append("Schema root must be a JSON object.")
        return result

    draft = schema.get("$schema")
    result.draft = draft if isinstance(draft, str) else None
    if draft != DRAFT_2020_12:
        result.errors.append("Schema $schema must be JSON Schema Draft 2020-12.")

    for ref in _walk_schema_refs(schema):
        if ref.startswith(("http://", "https://")):
            result.errors.append(f"Remote $ref is forbidden: {ref}")
        elif ref.startswith("#"):
            continue
        else:
            local = _resolve_in_package(root, ref)
            if local is None or not local.is_file():
                result.errors.append(f"Local $ref target missing or unsafe: {ref}")

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        result.errors.append(f"Invalid JSON Schema: {exc.message}")

    if is_output:
        if output_contract_type is None:
            result.errors.append(
                "Output schema validation requires manifest output_contract_type."
            )
        else:
            result.errors.extend(
                validate_output_contract_schema(schema, output_contract_type)
            )

    result.valid = len(result.errors) == 0
    return result


def validate_skill_package(
    package_path: Path,
    mode: SkillValidationMode = SkillValidationMode.CANDIDATE,
) -> SkillPackageValidationReport:
    """Validate a Skill package read-only; never executes package content."""
    report = SkillPackageValidationReport(
        package_path=str(package_path),
        validation_mode=mode,
        validator_version=VALIDATOR_VERSION,
    )

    if mode == SkillValidationMode.REGISTRY_READINESS:
        report.add_warning(
            code="mode_not_implemented",
            message="Validation mode 'registry_readiness' is not fully implemented.",
            rule_reference="SKILL-01.3",
        )

    try:
        root = _resolve_package_root(package_path)
    except SkillPackageNotFoundError as exc:
        report.add_error(code=exc.code, message=str(exc), rule_reference="RFC-SKILL-002")
        return report.finalize()

    manifest_path = root / MANIFEST_FILENAME
    skill_md_path = root / SKILL_MD_FILENAME

    if not manifest_path.is_file():
        report.add_error(
            code="skill_manifest_missing",
            message="manifest.yaml is required.",
            location=MANIFEST_FILENAME,
            rule_reference="RFC-SKILL-002",
        )
        return report.finalize()

    if not skill_md_path.is_file():
        report.missing_files.append(SKILL_MD_FILENAME)
        report.add_error(
            code="skill_md_missing",
            message="SKILL.md is required.",
            location=SKILL_MD_FILENAME,
            rule_reference="RFC-SKILL-002",
        )

    # Path boundary and symlink scan
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            report.forbidden_files.append(rel)
            report.add_error(
                code="security_symlink_forbidden",
                message="Symlinks are forbidden inside Skill packages.",
                location=rel,
                rule_reference="RFC-SKILL-003",
            )
            continue
        if ".." in path.parts:
            report.add_error(
                code="skill_package_path_violation",
                message="Path traversal is forbidden.",
                location=rel,
                rule_reference="RFC-SKILL-002",
            )

    manifest: SkillManifest | None = None
    raw_manifest: dict[str, Any] | None = None
    try:
        raw_manifest = parse_manifest_bytes(manifest_path.read_bytes())
        forbidden_keys = _collect_forbidden_manifest_keys(raw_manifest)
        for location, key in forbidden_keys:
            report.add_error(
                code="security_forbidden_manifest_key",
                message=f"Forbidden manifest key detected: {key}",
                location=location,
                rule_reference="RFC-SKILL-003",
                remediation_hint=(
                    "Remove secret-like keys from machine-readable manifest configuration."
                ),
            )
        manifest = SkillManifest.model_validate(raw_manifest)
    except SkillValidationError as exc:
        report.add_error(
            code=exc.code,
            message=str(exc),
            location=MANIFEST_FILENAME,
            rule_reference="RFC-SKILL-002",
        )
    except ValidationError as exc:
        report.add_error(
            code="skill_manifest_validation_error",
            message=str(exc),
            location=MANIFEST_FILENAME,
            rule_reference="RFC-SKILL-002",
        )

    if manifest is not None:
        report.skill_id = manifest.id
        report.skill_version = manifest.version
        report.status = manifest.status
        report.manifest = manifest
        report.normalized_manifest = manifest.normalized_registry_snapshot()

        if mode == SkillValidationMode.QUARANTINE_IMPORT:
            _apply_quarantine_import_rules(report, manifest)
        elif mode == SkillValidationMode.CANDIDATE:
            if manifest.status not in CANDIDATE_ALLOWED_STATUSES:
                report.add_error(
                    code="lifecycle_status_not_candidate",
                    message=(
                        "Candidate validation requires status candidate or quarantined; "
                        f"got {manifest.status}."
                    ),
                    location="status",
                    rule_reference="RFC-SKILL-001",
                )
            if manifest.status == SkillLifecycleStatus.ACTIVE:
                report.add_error(
                    code="lifecycle_active_forbidden",
                    message="Active status is forbidden for candidate package validation.",
                    location="status",
                    rule_reference="RFC-SKILL-001",
                )

            if manifest.allowed_tools:
                report.add_error(
                    code="security_allowed_tools_nonempty",
                    message="allowed_tools must be empty for candidate skeleton packages.",
                    location="allowed_tools",
                    rule_reference="RFC-SKILL-003",
                )
            if manifest.network_policy.default != SkillNetworkPolicyDefault.DENY:
                report.add_error(
                    code="security_network_not_deny",
                    message="network_policy.default must be deny.",
                    location="network_policy.default",
                    rule_reference="RFC-SKILL-003",
                )
            if manifest.script_policy.enabled:
                report.add_error(
                    code="security_scripts_enabled",
                    message="script_policy.enabled must be false in SKILL-01.2.",
                    location="script_policy.enabled",
                    rule_reference="RFC-SKILL-003",
                )
            if manifest.activation_conditions.executable:
                report.add_error(
                    code="security_executable_flag",
                    message=(
                        "activation_conditions.executable must be false for read-only packages."
                    ),
                    location="activation_conditions.executable",
                    rule_reference="RFC-SKILL-003",
                )

        resolved_output_contract = resolve_output_contract_type(manifest)
        if resolved_output_contract is None:
            report.add_error(
                code="skill_output_contract_type_missing",
                message=(
                    "Manifest must declare output_contract_type for new packages; "
                    "legacy frozen versions use compatibility mapping only."
                ),
                location="output_contract_type",
                rule_reference="SKILL-02.1.1",
            )

        for ref_path in (
            manifest.required_inputs.schema_ref,
            manifest.output_schema.schema_ref,
        ):
            report.referenced_files.append(ref_path)
            resolved = _resolve_in_package(root, ref_path)
            if resolved is None or not resolved.is_file():
                report.missing_files.append(ref_path)
                report.add_error(
                    code="skill_schema_missing",
                    message=f"Referenced schema not found: {ref_path}",
                    location=ref_path,
                    rule_reference="RFC-SKILL-002",
                )
            else:
                schema_result = _validate_json_schema_file(
                    root=root,
                    schema_ref=ref_path,
                    is_output=ref_path == manifest.output_schema.schema_ref,
                    output_contract_type=(
                        resolved_output_contract
                        if ref_path == manifest.output_schema.schema_ref
                        else None
                    ),
                )
                report.schema_results.append(schema_result)
                if not schema_result.valid:
                    for err in schema_result.errors:
                        report.add_error(
                            code="skill_schema_invalid",
                            message=err,
                            location=ref_path,
                            rule_reference="RFC-SKILL-002",
                        )

        if manifest.test_suite.manifest:
            report.referenced_files.append(manifest.test_suite.manifest)
            test_manifest = _resolve_in_package(root, manifest.test_suite.manifest)
            if test_manifest is None or not test_manifest.is_file():
                report.missing_files.append(manifest.test_suite.manifest)
                report.add_error(
                    code="test_suite_manifest_missing",
                    message=(
                        "Referenced test suite manifest missing: "
                        f"{manifest.test_suite.manifest}"
                    ),
                    location=manifest.test_suite.manifest,
                    rule_reference="RFC-SKILL-002",
                )

    if skill_md_path.is_file():
        skill_md_text = skill_md_path.read_text(encoding="utf-8")
        if SKILL_MD_FORBIDDEN_PATTERNS.search(skill_md_text):
            report.add_error(
                code="security_skill_md_permission_logic",
                message="SKILL.md must not contain permission or credential configuration.",
                location=SKILL_MD_FILENAME,
                rule_reference="RFC-SKILL-003",
            )

    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        for path in scripts_dir.rglob("*"):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                report.forbidden_files.append(rel)
                report.add_error(
                    code="security_scripts_directory",
                    message=(
                        "scripts/ directory content is forbidden while scripts remain disabled."
                    ),
                    location=rel,
                    rule_reference="RFC-SKILL-003",
                )

    scripts_globally_disabled = True
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        suffix = path.suffix.lower()
        if suffix not in EXECUTABLE_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if scripts_globally_disabled:
            report.forbidden_files.append(rel)
            report.add_error(
                code="security_executable_file",
                message=f"Executable or script file forbidden while scripts are disabled: {rel}",
                location=rel,
                rule_reference="RFC-SKILL-003",
            )

    try:
        report.package_hash = calculate_skill_package_hash(root)
        report.add_check("package_hash", True, detail=report.package_hash)
        if manifest is not None and report.package_hash is not None:
            conflict = frozen_package_hash_conflict(
                skill_id=manifest.id,
                version=manifest.version,
                package_hash=report.package_hash,
            )
            if conflict is not None:
                report.add_error(
                    code="immutable_version_hash_conflict",
                    message=conflict,
                    location="package_hash",
                    rule_reference="SKILL-02.2.1",
                    remediation_hint=(
                        "Restore frozen package bytes or publish a new semver version."
                    ),
                )
    except Exception as exc:
        code = getattr(exc, "code", "skill_hashing_error")
        report.add_error(code=code, message=str(exc), rule_reference="RFC-SKILL-002")
        report.add_check("package_hash", False, detail=str(exc))

    report.add_check("manifest_domain_contract", manifest is not None)
    report.add_check("read_only_validation", True, detail="No execution or import side effects.")
    return report.finalize()


__all__ = ["validate_skill_package", "parse_skill_manifest", "parse_manifest_bytes"]
