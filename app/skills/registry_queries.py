"""Pure read-only Skill registry queries (SKILL-01.3)."""

from __future__ import annotations

from app.schemas.contracts import SkillLifecycleStatus, SkillSourceType, SkillTenantScope
from app.skills.registry_contracts import (
    SkillEligibilityView,
    SkillRegistryQuery,
    SkillRegistryQueryResult,
    SkillRegistryRecord,
    SkillRegistrySnapshot,
    SkillRegistryVersionRecord,
    SkillRegistryView,
    SkillValidationStatus,
)
from app.skills.registry_errors import (
    SkillRegistryRecordNotFoundError,
    SkillRegistryVersionNotFoundError,
)

NOT_FOUND_MESSAGE = "Skill registry record was not found."


def _record_visible_to_tenant(
    record: SkillRegistryRecord,
    *,
    tenant_id: str | None,
    view: SkillRegistryView,
) -> bool:
    if view == SkillRegistryView.AUDIT:
        return True

    if record.lifecycle_status == SkillLifecycleStatus.REJECTED:
        return view == SkillRegistryView.AUDIT

    if record.source_type == SkillSourceType.EXTERNAL_IMPORT:
        return view == SkillRegistryView.INTERNAL_RESEARCH

    if record.tenant_scope == SkillTenantScope.TENANT_PRIVATE:
        if tenant_id is None:
            return False
        return record.owner_tenant_id == tenant_id

    return not (
        record.lifecycle_status == SkillLifecycleStatus.QUARANTINED
        and view == SkillRegistryView.NORMAL
    )


def _version_visible(
    version: SkillRegistryVersionRecord,
    *,
    tenant_id: str | None,
    view: SkillRegistryView,
) -> bool:
    pseudo_record = SkillRegistryRecord(
        skill_id=version.skill_id,
        name=version.name,
        lifecycle_status=version.lifecycle_status,
        source_type=version.source_type,
        tenant_scope=version.tenant_scope,
        owner=version.owner,
        owner_tenant_id=version.owner_tenant_id,
        capabilities=version.capabilities,
        dependencies=version.dependencies,
        runtime_compatibility=version.runtime_compatibility,
        created_at=version.recorded_at,
        updated_at=version.recorded_at,
        security_class=version.security_class,
    )
    return _record_visible_to_tenant(pseudo_record, tenant_id=tenant_id, view=view)


def derive_eligibility_view(
    version: SkillRegistryVersionRecord,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillEligibilityView:
    visible = _version_visible(version, tenant_id=tenant_id, view=view)
    status = version.lifecycle_status
    blockers: list[str] = []
    warnings: list[str] = []

    production_eligible = status in {
        SkillLifecycleStatus.ACTIVE,
        SkillLifecycleStatus.TENANT_ACTIVE,
    }
    selectable = (
        production_eligible
        and visible
        and version.validation_status == SkillValidationStatus.VALID
    )

    if status == SkillLifecycleStatus.CANDIDATE:
        production_eligible = False
        selectable = False
        blockers.append("candidate_not_production_eligible")
    elif status == SkillLifecycleStatus.QUARANTINED:
        production_eligible = False
        selectable = False
        blockers.append("quarantined_not_production_eligible")
    elif status == SkillLifecycleStatus.AUDITED:
        production_eligible = False
        selectable = False
        blockers.append("audited_not_production_eligible")
    elif status == SkillLifecycleStatus.APPROVED:
        production_eligible = False
        selectable = False
        blockers.append("approved_not_active")
    elif status == SkillLifecycleStatus.SUSPENDED:
        production_eligible = False
        selectable = False
        blockers.append("suspended_not_selectable")
    elif status == SkillLifecycleStatus.DEPRECATED:
        production_eligible = False
        selectable = False
        blockers.append("deprecated_not_selectable_for_new_work")
    elif status == SkillLifecycleStatus.ARCHIVED:
        production_eligible = False
        selectable = False
        blockers.append("archived_lineage_only")
    elif status == SkillLifecycleStatus.REJECTED:
        production_eligible = False
        selectable = False
        blockers.append("rejected")

    if version.validation_status != SkillValidationStatus.VALID:
        production_eligible = False
        selectable = False
        blockers.append("invalid_validation_status")

    if not visible:
        selectable = False
        blockers.append("not_visible_to_tenant")

    lineage_resolvable = status in {
        SkillLifecycleStatus.ACTIVE,
        SkillLifecycleStatus.DEPRECATED,
        SkillLifecycleStatus.SUSPENDED,
        SkillLifecycleStatus.ARCHIVED,
        SkillLifecycleStatus.CANDIDATE,
        SkillLifecycleStatus.QUARANTINED,
        SkillLifecycleStatus.AUDITED,
        SkillLifecycleStatus.APPROVED,
        SkillLifecycleStatus.TENANT_ACTIVE,
        SkillLifecycleStatus.TENANT_PRIVATE,
    }

    if version.warnings:
        warnings.extend(f"validation_warning:{issue.code}" for issue in version.warnings)

    return SkillEligibilityView(
        skill_id=version.skill_id,
        version=version.version,
        production_eligible=production_eligible,
        selectable_for_new_work=selectable,
        visible_to_tenant=visible,
        lineage_resolvable=lineage_resolvable,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def _filter_records(
    snapshot: SkillRegistrySnapshot,
    query: SkillRegistryQuery,
) -> list[SkillRegistryRecord]:
    results: list[SkillRegistryRecord] = []
    for record in snapshot.records:
        if query.skill_id is not None and record.skill_id != query.skill_id:
            continue
        if query.lifecycle_status is not None and record.lifecycle_status != query.lifecycle_status:
            continue
        if query.source_type is not None and record.source_type != query.source_type:
            continue
        if query.tenant_scope is not None and record.tenant_scope != query.tenant_scope:
            continue
        if query.owner is not None and record.owner != query.owner:
            continue
        if (
            query.validation_status is not None
            and record.validation_status != query.validation_status
        ):
            continue
        if query.capability is not None and query.capability not in record.capabilities:
            continue
        if (
            query.runtime_compatibility is not None
            and query.runtime_compatibility not in record.runtime_compatibility
        ):
            continue
        if query.package_hash is not None and record.package_hash != query.package_hash and all(
            version.package_hash != query.package_hash for version in record.versions
        ):
            continue
        if query.version is not None and query.version not in record.available_versions:
            continue
        if not _record_visible_to_tenant(
            record,
            tenant_id=query.tenant_id,
            view=query.view,
        ):
            continue
        if query.view == SkillRegistryView.NORMAL and record.lifecycle_status in {
            SkillLifecycleStatus.REJECTED,
            SkillLifecycleStatus.QUARANTINED,
        }:
            continue
        results.append(record)
    return sorted(results, key=lambda item: item.skill_id)


def query_registry(
    snapshot: SkillRegistrySnapshot,
    query: SkillRegistryQuery,
) -> SkillRegistryQueryResult:
    records = tuple(_filter_records(snapshot, query))
    return SkillRegistryQueryResult(records=records, total_count=len(records))


def get_skill(
    snapshot: SkillRegistrySnapshot,
    skill_id: str,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryRecord:
    query = SkillRegistryQuery(skill_id=skill_id, tenant_id=tenant_id, view=view)
    result = query_registry(snapshot, query)
    if not result.records:
        raise SkillRegistryRecordNotFoundError(NOT_FOUND_MESSAGE)
    return result.records[0]


def get_skill_version(
    snapshot: SkillRegistrySnapshot,
    skill_id: str,
    version: str,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryVersionRecord:
    try:
        record = get_skill(snapshot, skill_id, tenant_id=tenant_id, view=view)
    except SkillRegistryRecordNotFoundError as exc:
        raise SkillRegistryVersionNotFoundError(NOT_FOUND_MESSAGE) from exc

    for item in record.versions:
        if item.version == version:
            if not _version_visible(item, tenant_id=tenant_id, view=view):
                raise SkillRegistryVersionNotFoundError(NOT_FOUND_MESSAGE)
            return item
    raise SkillRegistryVersionNotFoundError(NOT_FOUND_MESSAGE)


def list_skills(
    snapshot: SkillRegistrySnapshot,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryQueryResult:
    return query_registry(
        snapshot,
        SkillRegistryQuery(tenant_id=tenant_id, view=view),
    )


def find_by_capability(
    snapshot: SkillRegistrySnapshot,
    capability: str,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryQueryResult:
    return query_registry(
        snapshot,
        SkillRegistryQuery(capability=capability, tenant_id=tenant_id, view=view),
    )


def find_visible_for_tenant(
    snapshot: SkillRegistrySnapshot,
    tenant_id: str,
    *,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryQueryResult:
    return query_registry(
        snapshot,
        SkillRegistryQuery(tenant_id=tenant_id, view=view),
    )


def find_by_status(
    snapshot: SkillRegistrySnapshot,
    status: SkillLifecycleStatus,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryQueryResult:
    return query_registry(
        snapshot,
        SkillRegistryQuery(lifecycle_status=status, tenant_id=tenant_id, view=view),
    )


def find_by_package_hash(
    snapshot: SkillRegistrySnapshot,
    package_hash: str,
    *,
    tenant_id: str | None = None,
    view: SkillRegistryView = SkillRegistryView.NORMAL,
) -> SkillRegistryQueryResult:
    return query_registry(
        snapshot,
        SkillRegistryQuery(package_hash=package_hash, tenant_id=tenant_id, view=view),
    )
