"""Quarantine import adapter pipeline (SKILL-01.4)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.contracts import (
    SkillLifecycleStatus,
    SkillManifest,
    SkillSourceType,
    SkillTenantScope,
)
from app.skills.package_validator import validate_skill_package
from app.skills.quarantine_contracts import (
    PLATFORM_NATIVE_SKILL_IDS,
    QuarantineImportLimits,
    QuarantineImportOutcome,
    QuarantineImportRequest,
    QuarantineImportResult,
    QuarantineImportState,
    QuarantineProvenanceRecord,
    QuarantineSourceType,
    QuarantineStaticFindingSeverity,
)
from app.skills.quarantine_errors import (
    SkillQuarantineError,
)
from app.skills.quarantine_inspection import (
    calculate_source_fingerprint,
    inspect_source_tree,
    materialize_package,
)
from app.skills.quarantine_paths import (
    generate_import_id,
    normalized_package_root,
    quarantine_workspace_root,
    reports_root,
    resolve_local_source,
)
from app.skills.registry_contracts import (
    SkillApprovalState,
    SkillProjectionOutcome,
    SkillRegistryProjectionResult,
    SkillRegistrySourceReference,
    SkillRegistryVersionRecord,
    SkillSecurityClass,
    SkillValidationStatus,
)
from app.skills.validation_contracts import (
    SkillPackageValidationReport,
    SkillValidationIssue,
    SkillValidationMode,
    SkillValidationSeverity,
)


def _path_hash(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()


def _sanitize_validation_report(
    report: SkillPackageValidationReport,
    *,
    path_reference: str,
) -> SkillPackageValidationReport:
    return report.model_copy(update={"package_path": path_reference})


def _issue(
    code: str,
    message: str,
    *,
    severity: SkillValidationSeverity = SkillValidationSeverity.ERROR,
) -> SkillValidationIssue:
    return SkillValidationIssue(
        code=code,
        severity=severity,
        message=message,
        rule_reference="RFC-SKILL-003",
    )


def _collect_source_claims(manifest: SkillManifest | None) -> dict[str, Any]:
    if manifest is None:
        return {}
    source_value = (
        manifest.source.value
        if isinstance(manifest.source, SkillSourceType)
        else manifest.source
    )
    return {
        "declared_status": manifest.status.value,
        "declared_source": source_value,
        "declared_tenant_scope": manifest.tenant_scope.value,
        "declared_allowed_tools": list(manifest.allowed_tools),
        "declared_network_default": manifest.network_policy.default.value,
        "declared_script_policy_enabled": manifest.script_policy.enabled,
        "declared_executable": manifest.activation_conditions.executable,
    }


def _unresolved_claims(source_claims: dict[str, Any]) -> tuple[str, ...]:
    unresolved: list[str] = []
    if source_claims.get("declared_status") not in {None, SkillLifecycleStatus.QUARANTINED.value}:
        unresolved.append("declared_lifecycle_status")
    if source_claims.get("declared_allowed_tools"):
        unresolved.append("declared_allowed_tools")
    if source_claims.get("declared_network_default") != "deny":
        unresolved.append("declared_network_access")
    if source_claims.get("declared_script_policy_enabled"):
        unresolved.append("declared_script_policy")
    if source_claims.get("declared_executable"):
        unresolved.append("declared_executable")
    return tuple(unresolved)


def project_quarantine_registry_record(
    report: SkillPackageValidationReport,
    *,
    recorded_at: datetime | None = None,
) -> SkillRegistryProjectionResult:
    if report.manifest is None or report.skill_id is None or report.skill_version is None:
        return SkillRegistryProjectionResult(
            outcome=SkillProjectionOutcome.INCOMPLETE,
            reason_code="missing_manifest_metadata",
        )
    if not report.valid:
        return SkillRegistryProjectionResult(
            outcome=SkillProjectionOutcome.REJECTED,
            reason_code="validation_invalid",
        )

    manifest = report.manifest
    timestamp = recorded_at or report.created_at.astimezone(UTC)
    normalized = report.normalized_manifest or manifest.normalized_registry_snapshot()

    version_record = SkillRegistryVersionRecord(
        skill_id=report.skill_id,
        version=report.skill_version,
        name=manifest.name,
        lifecycle_status=SkillLifecycleStatus.QUARANTINED,
        source_type=SkillSourceType.EXTERNAL_IMPORT,
        tenant_scope=SkillTenantScope.GLOBAL,
        owner=manifest.owner,
        owner_tenant_id=None,
        capabilities=tuple(sorted(manifest.capabilities)),
        dependencies=tuple(),
        runtime_compatibility=tuple(sorted(manifest.runtime_compatibility)),
        quality_state=manifest.quality_threshold.current_state,
        package_hash=report.package_hash or "",
        validator_version=report.validator_version,
        validation_status=SkillValidationStatus.VALID,
        provenance=manifest.provenance,
        normalized_manifest=normalized,
        source_reference=SkillRegistrySourceReference(
            package_hash=report.package_hash or "",
            validator_version=report.validator_version,
            validation_status=SkillValidationStatus.VALID,
            validation_mode=report.validation_mode.value,
            validated_at=report.created_at.astimezone(UTC),
            warning_count=len(report.warnings),
            security_finding_count=len(report.security_findings),
        ),
        security_class=SkillSecurityClass.QUARANTINED,
        approval_state=SkillApprovalState.UNKNOWN,
        evidence_policy_summary=None,
        approval_policy_summary=None,
        warnings=tuple(report.warnings),
        security_findings=tuple(report.security_findings),
        recorded_at=timestamp,
    )
    return SkillRegistryProjectionResult(
        outcome=SkillProjectionOutcome.PROJECTED,
        reason_code="quarantine_overlay_applied",
        version_record=version_record,
    )


def _detect_conflicts(
    *,
    request: QuarantineImportRequest,
    source_fingerprint: str,
    manifest: SkillManifest | None,
    materialized_hash: str | None,
    state: QuarantineImportState,
) -> list[SkillValidationIssue]:
    issues: list[SkillValidationIssue] = []
    if source_fingerprint in state.seen_source_fingerprints:
        issues.append(
            _issue(
                "quarantine_duplicate_source_fingerprint",
                "Source fingerprint was already imported in this session.",
            )
        )

    if manifest is not None:
        key = (manifest.id, manifest.version)
        existing_hash = state.seen_id_version_hashes.get(key)
        if (
            existing_hash is not None
            and materialized_hash is not None
            and existing_hash != materialized_hash
        ):
            issues.append(
                _issue(
                    "quarantine_duplicate_id_version_hash",
                    "Same skill_id and version already imported with a different package hash.",
                )
            )
        if manifest.id in PLATFORM_NATIVE_SKILL_IDS:
            issues.append(
                _issue(
                    "quarantine_platform_native_id_collision",
                    "Imported skill_id collides with a platform-native Skill.",
                )
            )
        if request.expected_skill_id and manifest.id != request.expected_skill_id:
            issues.append(
                _issue(
                    "quarantine_expected_skill_id_mismatch",
                    "Package skill_id does not match expected_skill_id.",
                )
            )
        if request.expected_version and manifest.version != request.expected_version:
            issues.append(
                _issue(
                    "quarantine_expected_version_mismatch",
                    "Package version does not match expected_version.",
                )
            )
        if manifest.source == SkillSourceType.PLATFORM_NATIVE:
            issues.append(
                _issue(
                    "quarantine_declared_source_type_mismatch",
                    "External import cannot declare platform_native source type.",
                    severity=SkillValidationSeverity.WARNING,
                )
            )
    return issues


def import_skill_package_to_quarantine(
    request: QuarantineImportRequest,
    *,
    quarantine_base_dir: Path,
    limits: QuarantineImportLimits | None = None,
    state: QuarantineImportState | None = None,
    imported_at: datetime | None = None,
) -> QuarantineImportResult:
    """Import a local external Skill package into isolated quarantine (read-only)."""
    effective_limits = limits or QuarantineImportLimits()
    import_state = state or QuarantineImportState()
    timestamp = imported_at or datetime.now(tz=UTC)
    import_id = generate_import_id()
    errors: list[SkillValidationIssue] = []
    warnings: list[SkillValidationIssue] = []

    try:
        source_root = resolve_local_source(Path(request.source_path))
    except SkillQuarantineError as exc:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            errors=(_issue(exc.code, str(exc)),),
            created_at=timestamp,
        )

    if not source_root.is_dir():
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            errors=(
                _issue(
                    "skill_quarantine_source_not_found",
                    "Source must be a local directory.",
                ),
            ),
            created_at=timestamp,
        )

    if request.source_type == QuarantineSourceType.LOCAL_ARCHIVE:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            errors=(
                _issue(
                    "skill_quarantine_unsupported_file",
                    "Archive import is deferred in SKILL-01.4; use local_directory.",
                ),
            ),
            created_at=timestamp,
        )

    try:
        static_findings, _, _ = inspect_source_tree(source_root, limits=effective_limits)
    except SkillQuarantineError as exc:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            errors=(_issue(exc.code, str(exc)),),
            created_at=timestamp,
        )

    static_errors = [
        finding
        for finding in static_findings
        if finding.severity == QuarantineStaticFindingSeverity.ERROR
    ]
    if static_errors:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            static_findings=tuple(static_findings),
            errors=tuple(_issue(item.code, item.message) for item in static_errors),
            created_at=timestamp,
        )

    source_fingerprint = calculate_source_fingerprint(source_root)
    workspace = quarantine_workspace_root(quarantine_base_dir, import_id)
    if str(workspace.resolve()) in import_state.reserved_import_paths:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.CONFLICT,
            source_fingerprint=source_fingerprint,
            errors=(
                _issue(
                    "quarantine_workspace_exists",
                    "Quarantine workspace already reserved.",
                ),
            ),
            created_at=timestamp,
        )

    import_state.reserved_import_paths.add(str(workspace.resolve()))
    normalized_root = normalized_package_root(workspace)
    try:
        materialize_package(source_root, normalized_root, limits=effective_limits)
    except SkillQuarantineError as exc:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            source_fingerprint=source_fingerprint,
            errors=(_issue(exc.code, str(exc)),),
            created_at=timestamp,
        )

    materialized_hash = calculate_source_fingerprint(normalized_root)
    validation_report = validate_skill_package(
        normalized_root,
        mode=SkillValidationMode.QUARANTINE_IMPORT,
    )
    validation_report = _sanitize_validation_report(validation_report, path_reference=import_id)

    manifest = validation_report.manifest
    source_claims = _collect_source_claims(manifest)
    unresolved = _unresolved_claims(source_claims)
    conflict_issues = _detect_conflicts(
        request=request,
        source_fingerprint=source_fingerprint,
        manifest=manifest,
        materialized_hash=materialized_hash,
        state=import_state,
    )
    errors.extend(conflict_issues)
    warnings.extend(
        issue for issue in conflict_issues if issue.severity == SkillValidationSeverity.WARNING
    )

    if any(issue.severity == SkillValidationSeverity.ERROR for issue in conflict_issues):
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.CONFLICT,
            source_fingerprint=source_fingerprint,
            materialized_package_hash=materialized_hash,
            package_validation_report=validation_report,
            static_findings=tuple(static_findings),
            errors=tuple(errors),
            warnings=tuple(warnings),
            quarantine_path_reference=import_id,
            created_at=timestamp,
        )

    if not validation_report.valid or manifest is None:
        return QuarantineImportResult(
            import_id=import_id,
            outcome=QuarantineImportOutcome.REJECTED,
            source_fingerprint=source_fingerprint,
            materialized_package_hash=materialized_hash,
            package_validation_report=validation_report,
            static_findings=tuple(static_findings),
            errors=tuple(errors) + tuple(validation_report.errors),
            warnings=tuple(warnings) + tuple(validation_report.warnings),
            quarantine_path_reference=import_id,
            created_at=timestamp,
        )

    provenance = QuarantineProvenanceRecord(
        import_id=import_id,
        source_type=request.source_type,
        source_reference=request.source_reference,
        original_path_hash=_path_hash(source_root),
        source_fingerprint=source_fingerprint,
        materialized_package_hash=materialized_hash,
        declared_author=manifest.owner,
        declared_license=manifest.license,
        verified_author=None,
        verified_license=None,
        requested_by=request.requested_by,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        imported_at=timestamp,
        validator_version=validation_report.validator_version,
        source_claims=source_claims,
        unresolved_claims=unresolved,
    )

    registry_projection = project_quarantine_registry_record(
        validation_report,
        recorded_at=timestamp,
    )

    reports_root(workspace).mkdir(parents=True, exist_ok=True)
    metadata = {
        "import_id": import_id,
        "source_fingerprint": source_fingerprint,
        "materialized_package_hash": materialized_hash,
        "effective_status": SkillLifecycleStatus.QUARANTINED.value,
        "source_claims": source_claims,
        "unresolved_claims": list(unresolved),
    }
    (reports_root(workspace) / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    import_state.seen_source_fingerprints[source_fingerprint] = import_id
    import_state.seen_id_version_hashes[(manifest.id, manifest.version)] = materialized_hash

    return QuarantineImportResult(
        import_id=import_id,
        outcome=QuarantineImportOutcome.QUARANTINED,
        effective_status=SkillLifecycleStatus.QUARANTINED,
        source_fingerprint=source_fingerprint,
        materialized_package_hash=materialized_hash,
        package_validation_report=validation_report,
        provenance=provenance,
        static_findings=tuple(static_findings),
        errors=tuple(errors),
        warnings=tuple(warnings),
        quarantine_path_reference=import_id,
        registry_projection=registry_projection,
        audit_required=True,
        approval_required=True,
        executable=False,
        production_eligible=False,
        tenant_visible=False,
        created_at=timestamp,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import tempfile

    parser = argparse.ArgumentParser(
        description="Import a local Skill package candidate into quarantine (read-only).",
    )
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--requested-by", default="cli-operator")
    parser.add_argument("--source-reference", default="local-cli-import")
    parser.add_argument("--import-reason", default="Manual quarantine inspection")
    parser.add_argument("--correlation-id", default="cli")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="ms-quarantine-") as tmp:
        request = QuarantineImportRequest(
            source_path=str(args.source_path),
            source_type=QuarantineSourceType.LOCAL_DIRECTORY,
            requested_by=args.requested_by,
            source_reference=args.source_reference,
            import_reason=args.import_reason,
            correlation_id=args.correlation_id,
        )
        result = import_skill_package_to_quarantine(request, quarantine_base_dir=Path(tmp))

    if args.json:
        print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
    else:
        print(f"outcome: {result.outcome.value}")
        print(f"import_id: {result.import_id}")
        print(f"effective_status: {result.effective_status}")
        print(f"audit_required: {result.audit_required}")
        if result.errors:
            print("errors:")
            for issue in result.errors:
                print(f"  - [{issue.code}] {issue.message}")
    return 0 if result.outcome.value == "quarantined" else 1


if __name__ == "__main__":
    raise SystemExit(main())
