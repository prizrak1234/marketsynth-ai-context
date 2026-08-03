"""H2.8E — Identity Generation Subsystem API (no new product skill)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import get_settings
from app.db.models.identity_generation import IdentityReferenceManifestTable
from app.db.models.reference_visual import ReferenceSetTable, ReferenceVisualAssetTable
from app.db.models.user import UserTable
from app.identity_generation.errors import identity_error_message
from app.identity_generation.manifest import build_identity_reference_manifest
from app.identity_generation.operator import IdentityQualificationOperator
from app.identity_generation.preflight import evaluate_identity_preflight
from app.identity_generation.recipes import list_identity_recipes
from app.identity_generation.registry import (
    serialize_registry_safe,
)
from app.schemas.contracts import (
    IdentityPaidApprovalChoice,
    IdentityQualificationRun,
    IdentityReferenceManifest,
)

router = APIRouter(prefix="/identity-generation", tags=["identity-generation"])


@router.get("/providers")
async def list_identity_providers(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    settings = get_settings()
    return {
        "subsystem": "identity_generation",
        "providers": serialize_registry_safe(settings),
        "active": (settings.image_generation_provider or "").strip().lower(),
    }


@router.get("/recipes")
async def list_recipes(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    return {
        "recipes": [r.model_dump(mode="json") for r in list_identity_recipes()],
    }


class IdentityReadinessQuery(BaseModel):
    reference_set_id: UUID | None = None
    primary_reference_id: UUID | None = None
    prompt: str = ""
    consent: bool = False
    paid_approval_granted: bool = False


@router.post("/readiness")
async def identity_readiness(
    body: IdentityReadinessQuery,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    settings = get_settings()
    ref_set = None
    rows: list[ReferenceVisualAssetTable] = []
    if body.reference_set_id:
        ref_set = await session.get(ReferenceSetTable, body.reference_set_id)
        if ref_set is None or ref_set.owner_id != current_user.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "reference_set_required",
                    "safe_message": identity_error_message("reference_set_required"),
                },
            )
        for aid in ref_set.reference_asset_ids or []:
            asset = await session.get(ReferenceVisualAssetTable, aid)
            if asset is not None:
                rows.append(asset)
    primary = body.primary_reference_id or (
        ref_set.primary_reference_id if ref_set else None
    )
    manifest = None
    if ref_set and rows:
        manifest = build_identity_reference_manifest(
            owner_id=current_user.id,
            reference_set_id=ref_set.id,
            reference_set_version=str(ref_set.updated_at or ref_set.id),
            subject_type=ref_set.subject_type,
            rows=rows,
            primary_reference_id=primary,
            settings=settings,
        )
    readiness = evaluate_identity_preflight(
        settings=settings,
        owner_id=current_user.id,
        reference_set=ref_set,
        reference_rows=rows,
        primary_reference_id=primary,
        consent=body.consent,
        prompt=body.prompt,
        identity_profile_present=True,
        paid_approval_granted=body.paid_approval_granted,
        manifest=manifest,
        estimated_calls=1,
    )
    payload = readiness.model_dump(mode="json")
    if manifest:
        payload["manifest_preview"] = {
            "immutable_hash": manifest.immutable_hash,
            "stored_count": manifest.stored_count,
            "identity_selected": manifest.references_selected_count,
            "style_selected": len(manifest.style_reference_ids)
            + len(manifest.appearance_reference_ids),
            "transmitted_count": manifest.references_provider_received_count,
            "transmitted_ids": [str(x) for x in manifest.transmitted_reference_ids],
            "selected_but_not_transmitted": [
                str(e.asset_id)
                for e in manifest.selected_entries
                if e.transmission_status == "selected_but_not_transmitted"
            ],
            "safe_transmit_note": identity_error_message("selected_but_not_transmitted")
            if manifest.references_provider_received_count
            < len(manifest.identity_reference_ids)
            else None,
        }
    return payload


class CreateManifestBody(BaseModel):
    reference_set_id: UUID
    primary_reference_id: UUID | None = None


@router.post("/manifests", response_model=IdentityReferenceManifest)
async def create_manifest(
    body: CreateManifestBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityReferenceManifest:
    settings = get_settings()
    ref_set = await session.get(ReferenceSetTable, body.reference_set_id)
    if ref_set is None or ref_set.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    rows: list[ReferenceVisualAssetTable] = []
    for aid in ref_set.reference_asset_ids or []:
        asset = await session.get(ReferenceVisualAssetTable, aid)
        if asset is not None:
            rows.append(asset)
    primary = body.primary_reference_id or ref_set.primary_reference_id
    manifest = build_identity_reference_manifest(
        owner_id=current_user.id,
        reference_set_id=ref_set.id,
        reference_set_version=str(ref_set.updated_at or ref_set.id),
        subject_type=ref_set.subject_type,
        rows=rows,
        primary_reference_id=primary,
        settings=settings,
    )
    row = IdentityReferenceManifestTable(
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
        created_at=manifest.created_at,
    )
    session.add(row)
    await session.commit()
    return manifest


@router.get("/manifests/{manifest_id}", response_model=IdentityReferenceManifest)
async def get_manifest(
    manifest_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityReferenceManifest:
    row = await session.get(IdentityReferenceManifestTable, manifest_id)
    if row is None or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    return IdentityReferenceManifest.model_validate(row.payload)


class CreateQualificationRunBody(BaseModel):
    reference_set_id: UUID
    prompt: str = Field(min_length=1, max_length=4000)
    baseline_asset_id: UUID | None = None
    primary_reference_id: UUID | None = None
    consent: bool = False


@router.post("/qualification-runs", response_model=IdentityQualificationRun)
async def create_qualification_run(
    body: CreateQualificationRunBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityQualificationRun:
    op = IdentityQualificationOperator(session, get_settings())
    try:
        return await op.create_run(
            owner_id=current_user.id,
            reference_set_id=body.reference_set_id,
            prompt=body.prompt,
            baseline_asset_id=body.baseline_asset_id,
            consent=body.consent,
            primary_reference_id=body.primary_reference_id,
        )
    except LookupError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "reference_set_required",
                "safe_message": identity_error_message("reference_set_required"),
            },
        ) from None


@router.get("/qualification-runs/{run_id}", response_model=IdentityQualificationRun)
async def get_qualification_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityQualificationRun:
    op = IdentityQualificationOperator(session, get_settings())
    run = await op.get_run(run_id=run_id, owner_id=current_user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="resource_not_found")
    return run


@router.post("/qualification-runs/{run_id}/advance", response_model=IdentityQualificationRun)
async def advance_qualification_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityQualificationRun:
    op = IdentityQualificationOperator(session, get_settings())
    try:
        return await op.advance(run_id=run_id, owner_id=current_user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="resource_not_found") from None


class ApproveCallsBody(BaseModel):
    choice: IdentityPaidApprovalChoice


@router.post(
    "/qualification-runs/{run_id}/approve-calls",
    response_model=IdentityQualificationRun,
)
async def approve_qualification_calls(
    run_id: UUID,
    body: ApproveCallsBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityQualificationRun:
    op = IdentityQualificationOperator(session, get_settings())
    try:
        return await op.approve_calls(
            run_id=run_id, owner_id=current_user.id, choice=body.choice
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="resource_not_found") from None


class OwnerReviewBody(BaseModel):
    review: str  # acceptable | partial | not_recognizable
    consistency_assist: str | None = None


@router.post(
    "/qualification-runs/{run_id}/owner-review",
    response_model=IdentityQualificationRun,
)
async def owner_review_qualification(
    run_id: UUID,
    body: OwnerReviewBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityQualificationRun:
    op = IdentityQualificationOperator(session, get_settings())
    try:
        return await op.record_owner_review(
            run_id=run_id,
            owner_id=current_user.id,
            review=body.review,
            consistency_assist=body.consistency_assist,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="resource_not_found") from None


@router.post(
    "/qualification-runs/{run_id}/cancel",
    response_model=IdentityQualificationRun,
)
async def cancel_qualification_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> IdentityQualificationRun:
    op = IdentityQualificationOperator(session, get_settings())
    try:
        return await op.cancel(run_id=run_id, owner_id=current_user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="resource_not_found") from None


@router.get("/error-messages")
async def list_error_messages(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    from app.identity_generation.errors import IDENTITY_ERROR_MESSAGES_RU

    return {"messages": IDENTITY_ERROR_MESSAGES_RU}
