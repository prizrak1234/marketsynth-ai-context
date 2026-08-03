"""Reference visual assets API (Phase H2.6A-R)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import get_settings
from app.db.models.reference_visual import ReferenceSetTable, ReferenceVisualAssetTable
from app.db.models.user import UserTable
from app.db.base import utc_now
from app.reference_images.service import ReferenceImageService, ReferenceUploadError
from app.schemas.contracts import (
    ReferenceAssetPurpose,
    ReferenceSet,
    ReferenceSetStatus,
    ReferenceSubjectType,
    ReferenceVisualAsset,
)

router = APIRouter(tags=["reference-visual-assets"])


def _set_contract(row: ReferenceSetTable) -> ReferenceSet:
    return ReferenceSet(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        user_request_id=row.user_request_id,
        title=row.title,
        subject_type=row.subject_type,
        preservation_goal=row.preservation_goal,
        status=row.status,
        reference_asset_ids=[UUID(str(x)) for x in (row.reference_asset_ids or [])],
        primary_reference_id=row.primary_reference_id,
        identity_notes=row.identity_notes,
        immutable_traits=[str(x) for x in (row.immutable_traits or [])],
        allowed_variations=[str(x) for x in (row.allowed_variations or [])],
        forbidden_changes=[str(x) for x in (row.forbidden_changes or [])],
        consent_confirmed=bool(row.consent_confirmed),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class ReferenceSetCreateBody(BaseModel):
    title: str = "Reference set"
    subject_type: ReferenceSubjectType = ReferenceSubjectType.MIXED
    user_request_id: UUID | None = None
    project_id: UUID | None = None
    identity_notes: str | None = None
    immutable_traits: list[str] = Field(default_factory=list)
    allowed_variations: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    consent_confirmed: bool = False


class ReferenceSetPatchBody(BaseModel):
    primary_reference_id: UUID | None = None
    identity_notes: str | None = None
    immutable_traits: list[str] | None = None
    allowed_variations: list[str] | None = None
    forbidden_changes: list[str] | None = None
    consent_confirmed: bool | None = None
    status: ReferenceSetStatus | None = None


@router.get("/reference-visual-assets/limits")
async def reference_limits(
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    _ = current_user
    s = get_settings()
    return {
        "max_count": s.reference_image_max_count,
        "max_bytes_per_file": s.reference_image_max_bytes_per_file,
        "max_total_bytes": s.reference_image_max_total_bytes,
        "min_width": s.reference_image_min_width,
        "min_height": s.reference_image_min_height,
        "provider_max_images": s.reference_provider_max_images,
        "accepted_mime": ["image/png", "image/jpeg", "image/webp"],
        "identity_promise": "maximize_not_guarantee",
        "honest_copy_ru": (
            "Marketsynth использует несколько референсов и режим повышенной точности, "
            "чтобы максимально сохранить внешность, стиль и узнаваемые особенности. "
            "Перед использованием результат необходимо проверить."
        ),
    }


@router.post("/reference-sets", response_model=ReferenceSet, status_code=status.HTTP_201_CREATED)
async def create_reference_set(
    body: ReferenceSetCreateBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ReferenceSet:
    service = ReferenceImageService(session, get_settings())
    row = await service.create_set(
        owner_id=current_user.id,
        title=body.title,
        subject_type=body.subject_type,
        user_request_id=body.user_request_id,
        project_id=body.project_id,
        identity_notes=body.identity_notes,
        immutable_traits=body.immutable_traits,
        allowed_variations=body.allowed_variations,
        forbidden_changes=body.forbidden_changes,
        consent_confirmed=body.consent_confirmed,
    )
    return _set_contract(row)


@router.get("/reference-sets/{set_id}", response_model=ReferenceSet)
async def get_reference_set(
    set_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ReferenceSet:
    row = await session.get(ReferenceSetTable, set_id)
    if row is None or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    return _set_contract(row)


@router.patch("/reference-sets/{set_id}", response_model=ReferenceSet)
async def patch_reference_set(
    set_id: UUID,
    body: ReferenceSetPatchBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ReferenceSet:
    row = await session.get(ReferenceSetTable, set_id)
    if row is None or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    if body.primary_reference_id is not None:
        ids = {str(x) for x in (row.reference_asset_ids or [])}
        if str(body.primary_reference_id) not in ids:
            raise HTTPException(status_code=400, detail="primary_not_in_set")
        row.primary_reference_id = body.primary_reference_id
    if body.identity_notes is not None:
        row.identity_notes = body.identity_notes
    if body.immutable_traits is not None:
        row.immutable_traits = list(body.immutable_traits)
    if body.allowed_variations is not None:
        row.allowed_variations = list(body.allowed_variations)
    if body.forbidden_changes is not None:
        row.forbidden_changes = list(body.forbidden_changes)
    if body.consent_confirmed is not None:
        row.consent_confirmed = body.consent_confirmed
    if body.status is not None:
        row.status = body.status
    row.updated_at = utc_now()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _set_contract(row)


@router.get("/reference-sets/{set_id}/selection")
async def selection_preview(
    set_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    service = ReferenceImageService(session, get_settings())
    try:
        result = await service.select_for_provider(owner_id=current_user.id, set_id=set_id)
    except ReferenceUploadError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": exc.code, "safe_message": exc.message},
        ) from exc
    return result.model_dump(mode="json")


@router.post(
    "/reference-sets/{set_id}/assets",
    response_model=ReferenceVisualAsset,
    status_code=status.HTTP_201_CREATED,
)
async def upload_reference_asset(
    set_id: UUID,
    file: UploadFile = File(...),
    asset_purpose: str = Form("other"),
    subject_type: str = Form("mixed"),
    consent_confirmed: bool = Form(False),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ReferenceVisualAsset:
    ref_set = await session.get(ReferenceSetTable, set_id)
    if ref_set is None or ref_set.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    payload = await file.read()
    service = ReferenceImageService(session, get_settings())
    try:
        purpose = ReferenceAssetPurpose(asset_purpose)
    except ValueError:
        purpose = ReferenceAssetPurpose.OTHER
    try:
        subject = ReferenceSubjectType(subject_type)
    except ValueError:
        subject = ReferenceSubjectType.MIXED
    try:
        return await service.upload(
            owner_id=current_user.id,
            payload=payload,
            filename=file.filename or "image.png",
            declared_mime=file.content_type,
            asset_purpose=purpose,
            subject_type=subject,
            user_request_id=ref_set.user_request_id,
            project_id=ref_set.project_id,
            set_id=set_id,
            consent_confirmed=consent_confirmed or bool(ref_set.consent_confirmed),
        )
    except ReferenceUploadError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": exc.code, "safe_message": exc.message},
        ) from exc


@router.get("/reference-visual-assets/{asset_id}", response_model=ReferenceVisualAsset)
async def get_reference_asset(
    asset_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ReferenceVisualAsset:
    row = await session.get(ReferenceVisualAssetTable, asset_id)
    if row is None or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    return ReferenceImageService(session)._to_asset_contract(row)


@router.get("/reference-visual-assets/{asset_id}/content")
async def get_reference_content(
    asset_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> FileResponse:
    row = await session.get(ReferenceVisualAssetTable, asset_id)
    if row is None or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    if not row.content_path or not Path(row.content_path).is_file():
        raise HTTPException(status_code=404, detail="content_unavailable")
    return FileResponse(
        row.content_path,
        media_type=row.mime_type,
        filename=row.original_filename,
    )


@router.get("/reference-sets/{set_id}/assets", response_model=list[ReferenceVisualAsset])
async def list_set_assets(
    set_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[ReferenceVisualAsset]:
    ref_set = await session.get(ReferenceSetTable, set_id)
    if ref_set is None or ref_set.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    service = ReferenceImageService(session)
    out: list[ReferenceVisualAsset] = []
    for aid in ref_set.reference_asset_ids or []:
        row = await session.get(ReferenceVisualAssetTable, UUID(str(aid)))
        if row and row.owner_id == current_user.id:
            out.append(service._to_asset_contract(row))
    return out


@router.delete("/reference-sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_reference_set(
    set_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> None:
    row = await session.get(ReferenceSetTable, set_id)
    if row is None or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="resource_not_found")
    row.status = ReferenceSetStatus.ARCHIVED
    row.updated_at = utc_now()
    for aid in row.reference_asset_ids or []:
        asset = await session.get(ReferenceVisualAssetTable, UUID(str(aid)))
        if asset and asset.owner_id == current_user.id:
            asset.archived_at = utc_now()
            session.add(asset)
    session.add(row)
    await session.commit()
