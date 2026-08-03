"""SKILL-01.3 — Skill registry read model tests."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.schemas.contracts import (
    SkillLifecycleStatus,
    SkillManifest,
    SkillSourceType,
    SkillTenantScope,
    skill_lifecycle_forbids_paused,
)
from app.skills.package_validator import validate_skill_package
from app.skills.registry_contracts import (
    SkillApprovalState,
    SkillProjectionOutcome,
    SkillRegistryQuery,
    SkillRegistryView,
    SkillSecurityClass,
    SkillValidationStatus,
    canonical_model_dict,
    compute_snapshot_hash,
)
from app.skills.registry_errors import (
    SkillRegistryRecordNotFoundError,
)
from app.skills.registry_projection import (
    build_registry_snapshot,
    detect_registry_conflicts,
    project_reports_to_snapshot,
    project_validation_report,
)
from app.skills.registry_queries import (
    derive_eligibility_view,
    find_by_capability,
    find_by_package_hash,
    find_by_status,
    get_skill,
    get_skill_version,
    list_skills,
    query_registry,
)
from app.skills.validation_contracts import SkillPackageValidationReport, SkillValidationMode

FROZEN_PACKAGE = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)
FROZEN_HASH = "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
FIXED_TIME = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def frozen_report() -> SkillPackageValidationReport:
    return validate_skill_package(FROZEN_PACKAGE)


@pytest.fixture
def frozen_projection(frozen_report: SkillPackageValidationReport):
    return project_validation_report(frozen_report, recorded_at=FIXED_TIME)


@pytest.fixture
def frozen_snapshot(frozen_projection):
    assert frozen_projection.version_record is not None
    return build_registry_snapshot(
        [frozen_projection.version_record],
        generated_at=FIXED_TIME,
    )


def _version_from_manifest(
    manifest: SkillManifest,
    *,
    version: str,
    status: SkillLifecycleStatus,
    package_hash: str,
    tenant_scope: SkillTenantScope = SkillTenantScope.GLOBAL,
    source_type: SkillSourceType = SkillSourceType.PLATFORM_NATIVE,
    owner: str = "Marketsynth Platform",
) -> SkillPackageValidationReport:
    patched = manifest.model_copy(
        update={
            "version": version,
            "status": status,
            "tenant_scope": tenant_scope,
            "source": source_type,
            "owner": owner,
        }
    )
    return SkillPackageValidationReport(
        package_path="packages/skills/test",
        skill_id=patched.id,
        skill_version=version,
        status=status,
        valid=True,
        validation_mode=SkillValidationMode.CANDIDATE,
        package_hash=package_hash,
        normalized_manifest=patched.normalized_registry_snapshot(),
        validator_version="0.1.0",
        manifest=patched,
        created_at=FIXED_TIME,
    )


def _manifest_from_frozen(frozen_report: SkillPackageValidationReport) -> SkillManifest:
    assert frozen_report.manifest is not None
    return frozen_report.manifest


def test_01_valid_report_projects_to_version_record(
    frozen_report: SkillPackageValidationReport,
) -> None:
    projection = project_validation_report(frozen_report, recorded_at=FIXED_TIME)
    assert projection.outcome == SkillProjectionOutcome.PROJECTED
    assert projection.version_record is not None
    assert projection.version_record.skill_id == "ms.skill.market_validation"


def test_02_candidate_remains_candidate(frozen_projection) -> None:
    assert frozen_projection.version_record is not None
    assert frozen_projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_03_validation_does_not_imply_approval(frozen_projection) -> None:
    assert frozen_projection.version_record is not None
    assert frozen_projection.version_record.approval_state == SkillApprovalState.UNKNOWN
    assert frozen_projection.version_record.lifecycle_status != SkillLifecycleStatus.APPROVED


def test_04_frozen_package_hash_preserved(frozen_projection) -> None:
    assert frozen_projection.version_record is not None
    assert frozen_projection.version_record.package_hash == FROZEN_HASH


def test_05_invalid_report_cannot_become_eligible(
    frozen_report: SkillPackageValidationReport,
) -> None:
    invalid = frozen_report.model_copy(update={"valid": False})
    projection = project_validation_report(invalid)
    assert projection.outcome == SkillProjectionOutcome.REJECTED
    assert projection.version_record is None


def test_06_projection_is_deterministic(frozen_report: SkillPackageValidationReport) -> None:
    first = project_validation_report(frozen_report, recorded_at=FIXED_TIME)
    second = project_validation_report(frozen_report, recorded_at=FIXED_TIME)
    assert canonical_model_dict(first) == canonical_model_dict(second)


def test_07_snapshot_serialization_deterministic(frozen_snapshot) -> None:
    first = canonical_model_dict(frozen_snapshot)
    second = canonical_model_dict(frozen_snapshot)
    assert first == second


def test_08_snapshot_hash_deterministic(frozen_snapshot) -> None:
    assert frozen_snapshot.snapshot_hash == compute_snapshot_hash(frozen_snapshot)


def test_09_record_ordering_stable(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    records = [
        project_validation_report(
            _version_from_manifest(
                manifest,
                version="0.1.0",
                status=SkillLifecycleStatus.CANDIDATE,
                package_hash="a" * 64,
            ),
            recorded_at=FIXED_TIME,
        ).version_record,
        project_validation_report(
            _version_from_manifest(
                manifest,
                version="0.2.0",
                status=SkillLifecycleStatus.CANDIDATE,
                package_hash="b" * 64,
            ),
            recorded_at=FIXED_TIME,
        ).version_record,
    ]
    assert all(record is not None for record in records)
    snapshot = build_registry_snapshot(
        [record for record in records if record],
        generated_at=FIXED_TIME,
    )
    assert snapshot.records[0].latest_known_version == "0.2.0"
    assert snapshot.records[0].available_versions == ("0.1.0", "0.2.0")


def test_10_exact_skill_lookup(frozen_snapshot) -> None:
    record = get_skill(frozen_snapshot, "ms.skill.market_validation")
    assert record.skill_id == "ms.skill.market_validation"


def test_11_version_lookup(frozen_snapshot) -> None:
    version = get_skill_version(frozen_snapshot, "ms.skill.market_validation", "0.1.0")
    assert version.version == "0.1.0"


def test_12_capability_lookup(frozen_snapshot) -> None:
    result = find_by_capability(frozen_snapshot, "market_evidence_assessment")
    assert result.total_count == 1


def test_13_status_filtering(frozen_snapshot) -> None:
    result = find_by_status(frozen_snapshot, SkillLifecycleStatus.CANDIDATE)
    assert result.total_count == 1


def test_14_source_type_filtering(frozen_snapshot) -> None:
    result = query_registry(
        frozen_snapshot,
        SkillRegistryQuery(source_type=SkillSourceType.PLATFORM_NATIVE),
    )
    assert result.total_count == 1


def test_15_package_hash_lookup(frozen_snapshot) -> None:
    result = find_by_package_hash(frozen_snapshot, FROZEN_HASH)
    assert result.total_count == 1


def test_16_global_skill_visible_to_arbitrary_tenant(frozen_snapshot) -> None:
    record = get_skill(
        frozen_snapshot,
        "ms.skill.market_validation",
        tenant_id="tenant-alpha",
    )
    assert record.tenant_scope == SkillTenantScope.GLOBAL


def test_17_tenant_private_visible_to_owner(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    report = _version_from_manifest(
        manifest,
        version="0.1.0",
        status=SkillLifecycleStatus.TENANT_PRIVATE,
        package_hash="c" * 64,
        tenant_scope=SkillTenantScope.TENANT_PRIVATE,
        owner="tenant-alpha",
    )
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    snapshot = build_registry_snapshot([projection.version_record], generated_at=FIXED_TIME)
    record = get_skill(snapshot, manifest.id, tenant_id="tenant-alpha")
    assert record.owner_tenant_id == "tenant-alpha"


def test_18_tenant_private_invisible_to_other_tenant(
    frozen_report: SkillPackageValidationReport,
) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    report = _version_from_manifest(
        manifest,
        version="0.1.0",
        status=SkillLifecycleStatus.TENANT_PRIVATE,
        package_hash="d" * 64,
        tenant_scope=SkillTenantScope.TENANT_PRIVATE,
        owner="tenant-alpha",
    )
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    snapshot = build_registry_snapshot([projection.version_record], generated_at=FIXED_TIME)
    with pytest.raises(SkillRegistryRecordNotFoundError, match="not found"):
        get_skill(snapshot, manifest.id, tenant_id="tenant-beta")


def test_19_cross_tenant_direct_lookup_safe_not_found(
    frozen_report: SkillPackageValidationReport,
) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    report = _version_from_manifest(
        manifest,
        version="0.1.0",
        status=SkillLifecycleStatus.TENANT_PRIVATE,
        package_hash="e" * 64,
        tenant_scope=SkillTenantScope.TENANT_PRIVATE,
        owner="tenant-alpha",
    )
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    snapshot = build_registry_snapshot([projection.version_record], generated_at=FIXED_TIME)
    with pytest.raises(SkillRegistryRecordNotFoundError, match="not found"):
        get_skill(snapshot, manifest.id, tenant_id="tenant-beta")


def test_20_cross_tenant_capability_query_leaks_no_metadata(
    frozen_report: SkillPackageValidationReport,
) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    private_manifest = manifest.model_copy(
        update={
            "id": "ms.skill.tenant_private_validation",
            "version": "0.1.0",
            "status": SkillLifecycleStatus.TENANT_PRIVATE,
            "tenant_scope": SkillTenantScope.TENANT_PRIVATE,
            "owner": "tenant-alpha",
        }
    )
    private = project_validation_report(
        SkillPackageValidationReport(
            package_path="packages/skills/private",
            skill_id=private_manifest.id,
            skill_version=private_manifest.version,
            status=private_manifest.status,
            valid=True,
            validation_mode=SkillValidationMode.CANDIDATE,
            package_hash="f" * 64,
            normalized_manifest=private_manifest.normalized_registry_snapshot(),
            validator_version="0.1.0",
            manifest=private_manifest,
            created_at=FIXED_TIME,
        ),
        recorded_at=FIXED_TIME,
    )
    public = project_validation_report(frozen_report, recorded_at=FIXED_TIME)
    snapshot = build_registry_snapshot(
        [private.version_record, public.version_record],
        generated_at=FIXED_TIME,
    )
    result = find_by_capability(snapshot, "market_evidence_assessment", tenant_id="tenant-beta")
    assert result.total_count == 1
    assert result.records[0].skill_id == "ms.skill.market_validation"


def test_21_candidate_not_selectable(frozen_projection) -> None:
    version = frozen_projection.version_record
    assert version is not None
    eligibility = derive_eligibility_view(version, tenant_id="tenant-alpha")
    assert eligibility.selectable_for_new_work is False
    assert eligibility.production_eligible is False


def test_22_quarantined_not_selectable(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    projection = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.QUARANTINED,
            package_hash="1" * 64,
        ),
        recorded_at=FIXED_TIME,
    )
    version = projection.version_record
    assert version is not None
    eligibility = derive_eligibility_view(version)
    assert eligibility.selectable_for_new_work is False


def test_23_active_selectable_when_constraints_pass(
    frozen_report: SkillPackageValidationReport,
) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    projection = project_validation_report(
        _version_from_manifest(
            manifest,
            version="1.0.0",
            status=SkillLifecycleStatus.ACTIVE,
            package_hash="2" * 64,
        ),
        recorded_at=FIXED_TIME,
    )
    version = projection.version_record
    assert version is not None
    eligibility = derive_eligibility_view(version, tenant_id="tenant-alpha")
    assert eligibility.selectable_for_new_work is True
    assert eligibility.production_eligible is True


def test_24_suspended_not_selectable(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    projection = project_validation_report(
        _version_from_manifest(
            manifest,
            version="1.0.0",
            status=SkillLifecycleStatus.SUSPENDED,
            package_hash="3" * 64,
        ),
        recorded_at=FIXED_TIME,
    )
    version = projection.version_record
    assert version is not None
    eligibility = derive_eligibility_view(version)
    assert eligibility.selectable_for_new_work is False


def test_25_archived_lineage_resolvable_only(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    projection = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.0.9",
            status=SkillLifecycleStatus.ARCHIVED,
            package_hash="4" * 64,
        ),
        recorded_at=FIXED_TIME,
    )
    version = projection.version_record
    assert version is not None
    eligibility = derive_eligibility_view(version)
    assert eligibility.lineage_resolvable is True
    assert eligibility.selectable_for_new_work is False


def test_26_rejected_hidden_from_normal_view(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    projection = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.REJECTED,
            package_hash="5" * 64,
        ),
        recorded_at=FIXED_TIME,
    )
    snapshot = build_registry_snapshot([projection.version_record], generated_at=FIXED_TIME)
    with pytest.raises(SkillRegistryRecordNotFoundError):
        get_skill(snapshot, manifest.id, view=SkillRegistryView.NORMAL)
    record = get_skill(snapshot, manifest.id, view=SkillRegistryView.AUDIT)
    assert record.lifecycle_status == SkillLifecycleStatus.REJECTED


def test_27_same_id_version_different_hash_conflict(
    frozen_report: SkillPackageValidationReport,
) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    first = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.CANDIDATE,
            package_hash="6" * 64,
        ),
        recorded_at=FIXED_TIME,
    ).version_record
    second = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.CANDIDATE,
            package_hash="7" * 64,
        ),
        recorded_at=FIXED_TIME,
    ).version_record
    conflicts = detect_registry_conflicts([first, second])  # type: ignore[list-item]
    assert any(conflict.conflict_code == "duplicate_skill_version_hash" for conflict in conflicts)


def test_28_duplicate_hash_detection(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    shared_hash = "8" * 64
    first = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.CANDIDATE,
            package_hash=shared_hash,
        ),
        recorded_at=FIXED_TIME,
    ).version_record
    second = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.2.0",
            status=SkillLifecycleStatus.CANDIDATE,
            package_hash=shared_hash,
        ),
        recorded_at=FIXED_TIME,
    ).version_record
    conflicts = detect_registry_conflicts([first, second])  # type: ignore[list-item]
    assert any(conflict.conflict_code == "duplicate_package_hash" for conflict in conflicts)


def test_29_conflict_not_auto_resolved(frozen_report: SkillPackageValidationReport) -> None:
    manifest = _manifest_from_frozen(frozen_report)
    first = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.CANDIDATE,
            package_hash="9" * 64,
        ),
        recorded_at=FIXED_TIME,
    ).version_record
    second = project_validation_report(
        _version_from_manifest(
            manifest,
            version="0.1.0",
            status=SkillLifecycleStatus.CANDIDATE,
            package_hash="0" * 64,
        ),
        recorded_at=FIXED_TIME,
    ).version_record
    conflicts = detect_registry_conflicts([first, second])  # type: ignore[list-item]
    snapshot = build_registry_snapshot([first, second], generated_at=FIXED_TIME)  # type: ignore[list-item]
    assert conflicts
    assert snapshot.record_count == 1


def test_30_no_paused_lifecycle_value() -> None:
    assert skill_lifecycle_forbids_paused()
    assert not hasattr(SkillLifecycleStatus, "PAUSED")


def test_31_snapshot_contains_no_secret_fields(frozen_snapshot) -> None:
    blob = json.dumps(canonical_model_dict(frozen_snapshot))
    for token in ("api_key", "client_secret", "password", "refresh_token"):
        assert token not in blob


def test_32_serialization_contains_no_absolute_package_path(frozen_snapshot) -> None:
    blob = json.dumps(canonical_model_dict(frozen_snapshot))
    assert "C:\\" not in blob
    assert "packages/skills/ms.skill.market_validation" not in blob


def test_33_registry_query_does_not_mutate_snapshot(frozen_snapshot) -> None:
    before = canonical_model_dict(frozen_snapshot)
    _ = list_skills(frozen_snapshot, tenant_id="tenant-alpha")
    after = canonical_model_dict(frozen_snapshot)
    assert before == after


def test_34_projection_does_not_mutate_validation_report(
    frozen_report: SkillPackageValidationReport,
) -> None:
    before = frozen_report.model_dump(mode="json")
    copied = copy.deepcopy(frozen_report)
    _ = project_validation_report(copied, recorded_at=FIXED_TIME)
    after = copied.model_dump(mode="json")
    assert before == after


def test_35_frozen_package_projection_result(frozen_report: SkillPackageValidationReport) -> None:
    snapshot, projections, conflicts = project_reports_to_snapshot(
        [frozen_report],
        generated_at=FIXED_TIME,
    )
    assert len(projections) == 1
    assert projections[0].outcome == SkillProjectionOutcome.PROJECTED
    assert not conflicts
    record = snapshot.records[0]
    assert record.skill_id == "ms.skill.market_validation"
    assert record.latest_known_version == "0.1.0"
    assert record.lifecycle_status == SkillLifecycleStatus.CANDIDATE
    assert record.source_type == SkillSourceType.PLATFORM_NATIVE
    assert record.tenant_scope == SkillTenantScope.GLOBAL
    assert record.validation_status == SkillValidationStatus.VALID
    assert record.package_hash == FROZEN_HASH
    version = get_skill_version(snapshot, record.skill_id, "0.1.0")
    eligibility = derive_eligibility_view(version, tenant_id="tenant-alpha")
    assert eligibility.production_eligible is False
    assert eligibility.selectable_for_new_work is False
    assert eligibility.lineage_resolvable is True
    assert version.security_class == SkillSecurityClass.READ_ONLY_CANDIDATE
