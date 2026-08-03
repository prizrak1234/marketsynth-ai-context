"""H2.8E — IdentityQualificationOperator (deterministic, resumable, no auto paid calls)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.base import utc_now
from app.db.models.identity_generation import (
    IdentityQualificationRunTable,
    IdentityReferenceManifestTable,
)
from app.db.models.reference_visual import ReferenceSetTable, ReferenceVisualAssetTable
from app.identity_generation.capability import classify_provider_capability
from app.identity_generation.errors import identity_error_message
from app.identity_generation.manifest import build_identity_reference_manifest
from app.identity_generation.preflight import evaluate_identity_preflight
from app.identity_generation.registry import get_provider_definition
from app.schemas.contracts import (
    IdentityPaidApprovalChoice,
    IdentityPaidApprovalRequest,
    IdentityQualificationRun,
    IdentityQualificationRunStatus,
    IdentityQualificationVariant,
    IdentityQualificationVariantStatus,
    IdentityReferenceManifest,
)


OPERATOR_STAGES = [
    "validate_preflight",
    "freeze_baseline",
    "build_reference_manifest",
    "prepare_test_variants",
    "request_paid_call_approval",
    "execute_approved_variants",
    "persist_results",
    "collect_automated_consistency_assistance",
    "request_owner_review",
    "classify_provider_capability",
    "write_qualification_report",
]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _variant_plan(provider_max: int) -> list[IdentityQualificationVariant]:
    """A executable if primary supported; B/C/D unsupported unless adapter multi-ref."""
    defs = [
        ("A", "primary face only", 1),
        ("B", "primary + best three-quarter", 2),
        ("C", "primary + three-quarter + profile", 3),
        ("D", "three identity + one style", 4),
    ]
    out: list[IdentityQualificationVariant] = []
    for code, label, needed in defs:
        if needed <= provider_max:
            status = IdentityQualificationVariantStatus.AWAITING_APPROVAL
            reason = None
        else:
            status = IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER
            reason = "provider_adapter_limit"
        out.append(
            IdentityQualificationVariant(
                variant_code=code,
                label=label,
                status=status,
                reason=reason,
            )
        )
    return out


def _to_contract(row: IdentityQualificationRunTable) -> IdentityQualificationRun:
    variants = [
        IdentityQualificationVariant.model_validate(v) for v in (row.variants or [])
    ]
    approval = None
    if row.paid_approval:
        approval = IdentityPaidApprovalRequest.model_validate(row.paid_approval)
    readiness = None
    if row.readiness_snapshot:
        from app.schemas.contracts import IdentityGenerationReadiness

        readiness = IdentityGenerationReadiness.model_validate(row.readiness_snapshot)
    return IdentityQualificationRun(
        id=row.id,
        owner_id=row.owner_id,
        status=row.status
        if isinstance(row.status, IdentityQualificationRunStatus)
        else IdentityQualificationRunStatus(str(row.status)),
        baseline_asset_id=row.baseline_asset_id,
        reference_set_id=row.reference_set_id,
        manifest_id=row.manifest_id,
        manifest_hash=row.manifest_hash,
        provider_code=row.provider_code,
        prompt_summary=row.prompt_summary,
        stage=row.stage,
        variants=variants,
        paid_approval=approval,
        readiness=readiness,
        capability_status=row.capability_status,
        owner_review_result=row.owner_review_result,
        consistency_assist=row.consistency_assist,
        report_summary=row.report_summary,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class IdentityQualificationOperator:
    """Explicit orchestration — not an autonomous agent."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def create_run(
        self,
        *,
        owner_id: UUID,
        reference_set_id: UUID,
        prompt: str,
        baseline_asset_id: UUID | None = None,
        consent: bool = False,
        primary_reference_id: UUID | None = None,
    ) -> IdentityQualificationRun:
        ref_set = await self._session.get(ReferenceSetTable, reference_set_id)
        if ref_set is None or ref_set.owner_id != owner_id:
            raise LookupError("reference_set_required")
        provider = get_provider_definition(self._settings)
        row = IdentityQualificationRunTable(
            id=uuid4(),
            owner_id=owner_id,
            status=IdentityQualificationRunStatus.DRAFT,
            baseline_asset_id=baseline_asset_id,
            reference_set_id=reference_set_id,
            provider_code=provider.provider_code,
            prompt_summary=(prompt or "")[:500],
            stage="validate_preflight",
            variants=[],
            paid_approval=None,
            readiness_snapshot=None,
            capability_status=provider.capability_status,
            created_at=_now(),
            updated_at=_now(),
            operator_state={
                "consent": bool(consent),
                "primary_reference_id": str(primary_reference_id)
                if primary_reference_id
                else None,
                "prompt": prompt[:4000],
            },
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return await self.advance(run_id=row.id, owner_id=owner_id)

    async def get_run(
        self, *, run_id: UUID, owner_id: UUID
    ) -> IdentityQualificationRun | None:
        row = await self._session.get(IdentityQualificationRunTable, run_id)
        if row is None or row.owner_id != owner_id:
            return None
        return _to_contract(row)

    async def advance(
        self, *, run_id: UUID, owner_id: UUID, max_steps: int = 6
    ) -> IdentityQualificationRun:
        row = await self._session.get(IdentityQualificationRunTable, run_id)
        if row is None or row.owner_id != owner_id:
            raise LookupError("qualification_run_not_found")
        if row.status in {
            IdentityQualificationRunStatus.CANCELLED,
            IdentityQualificationRunStatus.COMPLETED,
            IdentityQualificationRunStatus.AWAITING_PAID_APPROVAL,
            IdentityQualificationRunStatus.APPROVED,
            IdentityQualificationRunStatus.AWAITING_OWNER_REVIEW,
            IdentityQualificationRunStatus.PREFLIGHT_FAILED,
            IdentityQualificationRunStatus.FAILED,
        }:
            # Still allow preparing variants when awaiting approval was not yet set
            if row.status != IdentityQualificationRunStatus.DRAFT:
                return _to_contract(row)

        for _ in range(max_steps):
            row = await self._session.get(IdentityQualificationRunTable, run_id)
            if row is None:
                raise LookupError("qualification_run_not_found")
            if row.status in {
                IdentityQualificationRunStatus.CANCELLED,
                IdentityQualificationRunStatus.COMPLETED,
                IdentityQualificationRunStatus.AWAITING_PAID_APPROVAL,
                IdentityQualificationRunStatus.PREFLIGHT_FAILED,
                IdentityQualificationRunStatus.FAILED,
            }:
                break

            stage = row.stage or "validate_preflight"
            state = dict(row.operator_state or {})

            if stage == "validate_preflight":
                await self._stage_preflight(row, state)
            elif stage == "freeze_baseline":
                row.stage = "build_reference_manifest"
                row.updated_at = _now()
            elif stage == "build_reference_manifest":
                await self._stage_manifest(row, state)
            elif stage == "prepare_test_variants":
                provider = get_provider_definition(self._settings, row.provider_code)
                row.variants = [
                    v.model_dump(mode="json")
                    for v in _variant_plan(provider.maximum_identity_images)
                ]
                row.stage = "request_paid_call_approval"
                row.status = IdentityQualificationRunStatus.AWAITING_PAID_APPROVAL
                executable = [
                    v["variant_code"]
                    for v in row.variants
                    if v.get("status")
                    == IdentityQualificationVariantStatus.AWAITING_APPROVAL.value
                ]
                row.paid_approval = IdentityPaidApprovalRequest(
                    approval_id=uuid4(),
                    provider=row.provider_code,
                    model=getattr(self._settings, "openai_images_model", None),
                    call_count=1,
                    estimated_max_cost=None,
                    prompt_summary=row.prompt_summary,
                    manifest_id=row.manifest_id or uuid4(),
                    variants=executable[:1],
                    expires_at=_now() + timedelta(hours=24),
                    owner_confirmed=False,
                    choice=None,
                ).model_dump(mode="json")
                row.updated_at = _now()
            else:
                break

            self._session.add(row)
            await self._session.commit()

        row = await self._session.get(IdentityQualificationRunTable, run_id)
        assert row is not None
        return _to_contract(row)

    async def _stage_preflight(
        self, row: IdentityQualificationRunTable, state: dict[str, Any]
    ) -> None:
        ref_set = await self._session.get(ReferenceSetTable, row.reference_set_id)
        rows: list[ReferenceVisualAssetTable] = []
        if ref_set and ref_set.reference_asset_ids:
            for aid in ref_set.reference_asset_ids:
                asset = await self._session.get(ReferenceVisualAssetTable, aid)
                if asset is not None:
                    rows.append(asset)
        primary = state.get("primary_reference_id")
        primary_uuid = UUID(primary) if primary else getattr(ref_set, "primary_reference_id", None)
        consent = bool(state.get("consent"))
        readiness = evaluate_identity_preflight(
            settings=self._settings,
            owner_id=row.owner_id,
            reference_set=ref_set,
            reference_rows=rows,
            primary_reference_id=primary_uuid,
            consent=consent,
            prompt=str(state.get("prompt") or row.prompt_summary),
            identity_profile_present=True,  # profile built at execute time
            paid_approval_granted=False,
            estimated_calls=1,
        )
        row.readiness_snapshot = readiness.model_dump(mode="json")
        if not readiness.ready:
            hard = [c for c in readiness.blocking_conditions if c.blocking]
            # Allow progression to manifest even if paid approval not granted
            hard_codes = {c.code for c in hard} - {"paid_approval_required"}
            if hard_codes:
                row.status = IdentityQualificationRunStatus.PREFLIGHT_FAILED
                row.stage = "validate_preflight"
                row.report_summary = readiness.safe_summary
                row.updated_at = _now()
                return
        row.stage = "freeze_baseline"
        row.status = IdentityQualificationRunStatus.DRAFT
        row.updated_at = _now()
        # auto-continue one step
        row.stage = "build_reference_manifest"

    async def _stage_manifest(
        self, row: IdentityQualificationRunTable, state: dict[str, Any]
    ) -> None:
        ref_set = await self._session.get(ReferenceSetTable, row.reference_set_id)
        if ref_set is None:
            row.status = IdentityQualificationRunStatus.FAILED
            row.report_summary = identity_error_message("reference_set_required")
            row.updated_at = _now()
            return
        rows: list[ReferenceVisualAssetTable] = []
        for aid in ref_set.reference_asset_ids or []:
            asset = await self._session.get(ReferenceVisualAssetTable, aid)
            if asset is not None:
                rows.append(asset)
        primary = state.get("primary_reference_id")
        primary_uuid = UUID(primary) if primary else ref_set.primary_reference_id
        version = str(getattr(ref_set, "updated_at", "") or ref_set.id)
        manifest = build_identity_reference_manifest(
            owner_id=row.owner_id,
            reference_set_id=ref_set.id,
            reference_set_version=version,
            subject_type=ref_set.subject_type,
            rows=rows,
            primary_reference_id=primary_uuid,
            settings=self._settings,
            identity_profile_version="1.0",
            provider_code=row.provider_code,
        )
        # Persist immutable manifest (idempotent by hash for same run)
        existing = await self._session.execute(
            select(IdentityReferenceManifestTable).where(
                IdentityReferenceManifestTable.owner_id == row.owner_id,
                IdentityReferenceManifestTable.immutable_hash == manifest.immutable_hash,
            )
        )
        found = existing.scalars().first()
        if found is None:
            found = IdentityReferenceManifestTable(
                id=manifest.manifest_id,
                owner_id=manifest.owner_id,
                reference_set_id=manifest.reference_set_id,
                reference_set_version=manifest.reference_set_version,
                subject_type=manifest.subject_type,
                primary_reference_id=manifest.primary_reference_id,
                payload=manifest.model_dump(mode="json"),
                immutable_hash=manifest.immutable_hash,
                selection_policy_version=manifest.selection_policy_version,
                provider_code=manifest.provider_code,
                created_at=manifest.created_at or _now(),
            )
            self._session.add(found)
            await self._session.flush()
        row.manifest_id = found.id
        row.manifest_hash = found.immutable_hash
        # refresh readiness with manifest
        readiness = evaluate_identity_preflight(
            settings=self._settings,
            owner_id=row.owner_id,
            reference_set=ref_set,
            reference_rows=rows,
            primary_reference_id=primary_uuid,
            consent=bool(state.get("consent")),
            prompt=str(state.get("prompt") or row.prompt_summary),
            identity_profile_present=True,
            paid_approval_granted=False,
            manifest=IdentityReferenceManifest.model_validate(found.payload),
            estimated_calls=1,
        )
        row.readiness_snapshot = readiness.model_dump(mode="json")
        row.stage = "prepare_test_variants"
        row.updated_at = _now()

    async def approve_calls(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        choice: IdentityPaidApprovalChoice,
    ) -> IdentityQualificationRun:
        row = await self._session.get(IdentityQualificationRunTable, run_id)
        if row is None or row.owner_id != owner_id:
            raise LookupError("qualification_run_not_found")
        if row.status == IdentityQualificationRunStatus.CANCELLED:
            return _to_contract(row)

        approval = dict(row.paid_approval or {})
        approval["choice"] = choice.value
        approval["owner_confirmed"] = choice in {
            IdentityPaidApprovalChoice.APPROVE_ONE_DIAGNOSTIC,
            IdentityPaidApprovalChoice.APPROVE_FULL_COMPARISON,
        }

        if choice in {
            IdentityPaidApprovalChoice.REJECT,
            IdentityPaidApprovalChoice.CANCEL,
        }:
            row.status = IdentityQualificationRunStatus.CANCELLED
            row.stage = "request_paid_call_approval"
            approval["owner_confirmed"] = False
            row.paid_approval = approval
            row.updated_at = _now()
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)
            return _to_contract(row)

        variants = list(row.variants or [])
        if choice == IdentityPaidApprovalChoice.APPROVE_ONE_DIAGNOSTIC:
            approval["call_count"] = 1
            approval["variants"] = ["A"]
            for v in variants:
                if v.get("variant_code") == "A" and v.get("status") != (
                    IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER.value
                ):
                    v["status"] = IdentityQualificationVariantStatus.AWAITING_APPROVAL.value
                elif v.get("variant_code") != "A" and v.get("status") != (
                    IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER.value
                ):
                    v["status"] = IdentityQualificationVariantStatus.SKIPPED.value
        else:
            executable = [
                v
                for v in variants
                if v.get("status")
                != IdentityQualificationVariantStatus.UNSUPPORTED_BY_ADAPTER.value
            ]
            approval["call_count"] = len(executable)
            approval["variants"] = [v["variant_code"] for v in executable]
            for v in executable:
                v["status"] = IdentityQualificationVariantStatus.AWAITING_APPROVAL.value

        row.variants = variants
        row.paid_approval = approval
        row.status = IdentityQualificationRunStatus.APPROVED
        row.stage = "execute_approved_variants"
        row.updated_at = _now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_contract(row)

    async def record_owner_review(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        review: str,
        consistency_assist: str | None = None,
    ) -> IdentityQualificationRun:
        row = await self._session.get(IdentityQualificationRunTable, run_id)
        if row is None or row.owner_id != owner_id:
            raise LookupError("qualification_run_not_found")
        provider = get_provider_definition(self._settings, row.provider_code)
        decision = classify_provider_capability(
            provider_code=row.provider_code,
            supports_true_identity_mode=provider.supports_supporting_references,
            supports_supporting_references=provider.supports_supporting_references,
            owner_review=review,
            approved_failed_attempts=1
            if review in {"not_recognizable", "rejected", "different_person", "low"}
            else 0,
            automated_consistency=consistency_assist,
            decided_by="owner",
        )
        row.owner_review_result = review
        row.consistency_assist = consistency_assist
        row.capability_status = decision.capability_status
        row.status = IdentityQualificationRunStatus.COMPLETED
        row.stage = "write_qualification_report"
        row.report_summary = decision.rationale
        row.updated_at = _now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_contract(row)

    async def cancel(
        self, *, run_id: UUID, owner_id: UUID
    ) -> IdentityQualificationRun:
        row = await self._session.get(IdentityQualificationRunTable, run_id)
        if row is None or row.owner_id != owner_id:
            raise LookupError("qualification_run_not_found")
        row.status = IdentityQualificationRunStatus.CANCELLED
        row.updated_at = utc_now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_contract(row)

    async def mark_variant_executed(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        variant_code: str,
        asset_id: UUID,
        transmitted_ids: list[UUID],
    ) -> IdentityQualificationRun:
        row = await self._session.get(IdentityQualificationRunTable, run_id)
        if row is None or row.owner_id != owner_id:
            raise LookupError("qualification_run_not_found")
        if row.status != IdentityQualificationRunStatus.APPROVED and row.status != (
            IdentityQualificationRunStatus.RUNNING
        ):
            raise PermissionError("paid_approval_required")
        variants = list(row.variants or [])
        for v in variants:
            if v.get("variant_code") == variant_code:
                v["status"] = IdentityQualificationVariantStatus.EXECUTED.value
                v["asset_id"] = str(asset_id)
                v["transmitted_reference_ids"] = [str(x) for x in transmitted_ids]
                v["references_provider_received_count"] = len(transmitted_ids)
        row.variants = variants
        row.status = IdentityQualificationRunStatus.AWAITING_OWNER_REVIEW
        row.stage = "request_owner_review"
        row.updated_at = _now()
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_contract(row)
