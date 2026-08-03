"""Validation report → registry read model projection (SKILL-01.3)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.contracts import (
    SkillLifecycleStatus,
    SkillManifest,
    SkillSourceType,
    SkillTenantScope,
)
from app.skills.registry_contracts import (
    REGISTRY_SCHEMA_VERSION,
    SkillApprovalState,
    SkillDependencyRecord,
    SkillProjectionOutcome,
    SkillRegistryConflict,
    SkillRegistryProjectionResult,
    SkillRegistryRecord,
    SkillRegistrySnapshot,
    SkillRegistrySourceReference,
    SkillRegistryVersionRecord,
    SkillSecurityClass,
    SkillValidationStatus,
    compute_snapshot_hash,
    parse_semver,
)
from app.skills.validation_contracts import SkillPackageValidationReport


def _security_class_for_status(status: SkillLifecycleStatus) -> SkillSecurityClass:
    mapping = {
        SkillLifecycleStatus.CANDIDATE: SkillSecurityClass.READ_ONLY_CANDIDATE,
        SkillLifecycleStatus.QUARANTINED: SkillSecurityClass.QUARANTINED,
        SkillLifecycleStatus.AUDITED: SkillSecurityClass.AUDITED,
        SkillLifecycleStatus.APPROVED: SkillSecurityClass.APPROVED,
        SkillLifecycleStatus.ACTIVE: SkillSecurityClass.ACTIVE,
        SkillLifecycleStatus.SUSPENDED: SkillSecurityClass.RESTRICTED,
        SkillLifecycleStatus.DEPRECATED: SkillSecurityClass.RESTRICTED,
        SkillLifecycleStatus.ARCHIVED: SkillSecurityClass.ARCHIVED,
        SkillLifecycleStatus.REJECTED: SkillSecurityClass.REJECTED,
        SkillLifecycleStatus.TENANT_PRIVATE: SkillSecurityClass.READ_ONLY_CANDIDATE,
        SkillLifecycleStatus.TENANT_ACTIVE: SkillSecurityClass.ACTIVE,
    }
    return mapping.get(status, SkillSecurityClass.RESTRICTED)


def _approval_state_from_manifest(manifest: SkillManifest) -> SkillApprovalState:
    if manifest.status in {
        SkillLifecycleStatus.CANDIDATE,
        SkillLifecycleStatus.QUARANTINED,
        SkillLifecycleStatus.AUDITED,
    }:
        return SkillApprovalState.UNKNOWN
    if manifest.status == SkillLifecycleStatus.REJECTED:
        return SkillApprovalState.DENIED
    if manifest.status in {SkillLifecycleStatus.APPROVED, SkillLifecycleStatus.ACTIVE}:
        return SkillApprovalState.GRANTED
    return SkillApprovalState.UNKNOWN


def _summarize_evidence_policy(manifest: SkillManifest) -> str:
    classes = ", ".join(member.value for member in manifest.required_evidence.classes)
    return f"evidence_classes={classes}; rules={len(manifest.required_evidence.rules)}"


def _summarize_approval_policy(manifest: SkillManifest) -> str:
    stage_names = (
        "analysis_preparation",
        "verdict_presentation",
        "launch_or_execution_transition",
    )
    stages = [name for name in stage_names if getattr(manifest.approval_policy, name)]
    return f"approval_stages={','.join(stages) if stages else 'unknown'}"


def _dependency_records(manifest: SkillManifest) -> tuple[SkillDependencyRecord, ...]:
    records: list[SkillDependencyRecord] = []
    for dep in manifest.dependencies.declared_future_dependencies:
        records.append(
            SkillDependencyRecord(
                dependency_id=dep.id,
                relationship=dep.relationship.value,
                note=dep.note,
            )
        )
    return tuple(sorted(records, key=lambda item: item.dependency_id))


def _owner_tenant_id(manifest: SkillManifest) -> str | None:
    if manifest.tenant_scope == SkillTenantScope.TENANT_PRIVATE:
        return manifest.owner
    return None


def project_validation_report(
    report: SkillPackageValidationReport,
    *,
    recorded_at: datetime | None = None,
) -> SkillRegistryProjectionResult:
    """Pure projection from package validation report to version record."""
    if report.manifest is None or report.skill_id is None or report.skill_version is None:
        return SkillRegistryProjectionResult(
            outcome=SkillProjectionOutcome.INCOMPLETE,
            reason_code="missing_manifest_metadata",
            explanation="Validation report lacks manifest identity fields.",
        )

    if not report.valid:
        return SkillRegistryProjectionResult(
            outcome=SkillProjectionOutcome.REJECTED,
            reason_code="validation_invalid",
            explanation="Invalid validation report cannot produce eligible registry record.",
            remediation_hint="Fix package validation errors before registry projection.",
        )

    manifest = report.manifest
    normalized = report.normalized_manifest or manifest.normalized_registry_snapshot()
    timestamp = recorded_at or report.created_at.astimezone(UTC)

    version_record = SkillRegistryVersionRecord(
        skill_id=report.skill_id,
        version=report.skill_version,
        name=manifest.name,
        lifecycle_status=manifest.status,
        source_type=manifest.source,
        tenant_scope=manifest.tenant_scope,
        owner=manifest.owner,
        owner_tenant_id=_owner_tenant_id(manifest),
        capabilities=tuple(sorted(manifest.capabilities)),
        dependencies=_dependency_records(manifest),
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
        security_class=_security_class_for_status(manifest.status),
        approval_state=_approval_state_from_manifest(manifest),
        evidence_policy_summary=_summarize_evidence_policy(manifest),
        approval_policy_summary=_summarize_approval_policy(manifest),
        warnings=tuple(report.warnings),
        security_findings=tuple(report.security_findings),
        recorded_at=timestamp,
    )

    return SkillRegistryProjectionResult(
        outcome=SkillProjectionOutcome.PROJECTED,
        reason_code="projected_from_valid_report",
        version_record=version_record,
    )


def aggregate_skill_record(
    version_records: list[SkillRegistryVersionRecord],
) -> SkillRegistryRecord | None:
    if not version_records:
        return None

    sorted_versions = sorted(
        version_records,
        key=lambda item: parse_semver(item.version),
        reverse=True,
    )
    non_rejected = [
        record
        for record in sorted_versions
        if record.lifecycle_status != SkillLifecycleStatus.REJECTED
    ]
    latest = non_rejected[0] if non_rejected else sorted_versions[0]
    created_at = min(record.recorded_at for record in version_records)
    updated_at = max(record.recorded_at for record in version_records)

    return SkillRegistryRecord(
        skill_id=latest.skill_id,
        name=latest.name,
        latest_known_version=latest.version,
        available_versions=tuple(
            record.version
            for record in sorted(version_records, key=lambda item: parse_semver(item.version))
        ),
        lifecycle_status=latest.lifecycle_status,
        source_type=latest.source_type,
        tenant_scope=latest.tenant_scope,
        owner=latest.owner,
        owner_tenant_id=latest.owner_tenant_id,
        capabilities=latest.capabilities,
        dependencies=latest.dependencies,
        runtime_compatibility=latest.runtime_compatibility,
        quality_state=latest.quality_state,
        package_hash=latest.package_hash,
        validator_version=latest.validator_version,
        validation_status=latest.validation_status,
        provenance=latest.provenance,
        created_at=created_at,
        updated_at=updated_at,
        archived=latest.lifecycle_status == SkillLifecycleStatus.ARCHIVED,
        security_class=latest.security_class,
        approval_state=latest.approval_state,
        evidence_policy_summary=latest.evidence_policy_summary,
        approval_policy_summary=latest.approval_policy_summary,
        versions=tuple(
            sorted(version_records, key=lambda item: (parse_semver(item.version), item.version))
        ),
    )


def detect_registry_conflicts(
    version_records: list[SkillRegistryVersionRecord],
) -> list[SkillRegistryConflict]:
    conflicts: list[SkillRegistryConflict] = []
    by_id_version: dict[tuple[str, str], SkillRegistryVersionRecord] = {}
    by_hash: dict[str, list[SkillRegistryVersionRecord]] = {}

    for record in version_records:
        key = (record.skill_id, record.version)
        existing = by_id_version.get(key)
        if existing is not None and existing.package_hash != record.package_hash:
            conflicts.append(
                SkillRegistryConflict(
                    conflict_code="duplicate_skill_version_hash",
                    severity="error",
                    involved_records=(f"{record.skill_id}@{record.version}",),
                    explanation=(
                        "Same skill_id and version cannot map to different package hashes."
                    ),
                    remediation_hint="Resolve version immutability conflict before registry use.",
                )
            )
        by_id_version[key] = record

        by_hash.setdefault(record.package_hash, []).append(record)

    for package_hash, records in by_hash.items():
        if len(records) > 1:
            identities = tuple(
                sorted({f"{record.skill_id}@{record.version}" for record in records})
            )
            conflicts.append(
                SkillRegistryConflict(
                    conflict_code="duplicate_package_hash",
                    severity="warning",
                    involved_records=identities,
                    explanation=(
                        f"Package hash {package_hash[:12]}... appears under multiple identities."
                    ),
                    remediation_hint="Manual review recommended; may indicate duplicate import.",
                )
            )

    for record in version_records:
        if (
            record.tenant_scope == SkillTenantScope.TENANT_PRIVATE
            and record.source_type == SkillSourceType.PLATFORM_NATIVE
        ):
            conflicts.append(
                SkillRegistryConflict(
                    conflict_code="invalid_tenant_scope_source_combination",
                    severity="error",
                    involved_records=(f"{record.skill_id}@{record.version}",),
                    explanation="Tenant-private scope cannot use platform_native source type.",
                    remediation_hint="Correct manifest tenant_scope or source fields.",
                )
            )

    return conflicts


def build_registry_snapshot(
    version_records: list[SkillRegistryVersionRecord],
    *,
    generated_at: datetime | None = None,
    snapshot_id: str | None = None,
) -> SkillRegistrySnapshot:
    grouped: dict[str, list[SkillRegistryVersionRecord]] = {}
    for record in version_records:
        grouped.setdefault(record.skill_id, []).append(record)

    records = tuple(
        aggregate
        for aggregate in (
            aggregate_skill_record(group) for group in grouped.values()
        )
        if aggregate is not None
    )
    records = tuple(sorted(records, key=lambda item: item.skill_id))

    capability_index: dict[str, list[str]] = {}
    tenant_scope_index: dict[str, list[str]] = {}
    lifecycle_status_index: dict[str, list[str]] = {}

    for record in records:
        for capability in record.capabilities:
            capability_index.setdefault(capability, []).append(record.skill_id)
        tenant_scope_index.setdefault(record.tenant_scope.value, []).append(record.skill_id)
        lifecycle_status_index.setdefault(record.lifecycle_status.value, []).append(record.skill_id)

    source_hashes = tuple(
        sorted({record.package_hash for record in version_records if record.package_hash})
    )
    timestamp = generated_at or datetime.now(tz=UTC)

    snapshot = SkillRegistrySnapshot(
        snapshot_id=snapshot_id or "pending",
        generated_at=timestamp,
        records=records,
        source_hashes=source_hashes,
        registry_schema_version=REGISTRY_SCHEMA_VERSION,
        record_count=len(records),
        capability_index={
            key: tuple(sorted(values)) for key, values in sorted(capability_index.items())
        },
        tenant_scope_index={
            key: tuple(sorted(values)) for key, values in sorted(tenant_scope_index.items())
        },
        lifecycle_status_index={
            key: tuple(sorted(values)) for key, values in sorted(lifecycle_status_index.items())
        },
        snapshot_hash="pending",
    )
    snapshot_hash = compute_snapshot_hash(snapshot)
    return snapshot.model_copy(
        update={
            "snapshot_id": snapshot_id or snapshot_hash[:16],
            "snapshot_hash": snapshot_hash,
        }
    )


def project_reports_to_snapshot(
    reports: list[SkillPackageValidationReport],
    *,
    generated_at: datetime | None = None,
) -> tuple[SkillRegistrySnapshot, list[SkillRegistryProjectionResult], list[SkillRegistryConflict]]:
    projections = [project_validation_report(report) for report in reports]
    version_records = [
        projection.version_record
        for projection in projections
        if projection.outcome == SkillProjectionOutcome.PROJECTED and projection.version_record
    ]
    conflicts = detect_registry_conflicts(version_records)
    snapshot = build_registry_snapshot(version_records, generated_at=generated_at)
    return snapshot, projections, conflicts
