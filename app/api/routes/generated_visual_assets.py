"""Generated visual assets API (Phase H2.6A) — owner-scoped, no secrets."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import get_settings
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.user import UserTable
from app.media_generation.video_owner_acceptance_preview import is_canonical_owner_preview_asset
from app.schemas.contracts import GeneratedVisualAsset, UserRole
from app.services.design_image_generation_service import DesignImageGenerationService

router = APIRouter(prefix="/generated-visual-assets", tags=["generated-visual-assets"])


def _asset_visible_to_user(row: GeneratedVisualAssetTable, user: UserTable, asset_id: UUID) -> bool:
    if row.owner_id == user.id:
        return True
    return user.role in {UserRole.OWNER, UserRole.ADMIN} and is_canonical_owner_preview_asset(
        asset_id
    )


def _to_contract(row: GeneratedVisualAssetTable) -> GeneratedVisualAsset:
    meta = dict(row.generation_metadata or {})
    return GeneratedVisualAsset(
        id=row.id,
        owner_id=row.owner_id,
        user_request_id=row.user_request_id,
        skill_code=row.skill_code,
        skill_version=row.skill_version,
        knowledge_snapshot_id=row.knowledge_snapshot_id,
        provider=row.provider,
        model=row.model,
        provider_model=row.model,
        generation_mode=row.generation_mode,
        asset_type=row.asset_type,
        prompt_summary=row.prompt_summary,
        aspect_ratio=row.aspect_ratio,
        width=row.width,
        height=row.height,
        mime_type=row.mime_type,
        storage_uri=row.storage_uri,
        content_path=None,  # never expose filesystem path to clients
        checksum=row.checksum,
        status=row.status,
        safety_result=row.safety_result,
        generation_metadata=meta,
        error_category=row.error_category,
        created_at=row.created_at,
        reference_set_id=row.reference_set_id,
        used_reference_ids=[
            UUID(str(x)) if not isinstance(x, UUID) else x
            for x in (row.used_reference_ids or [])
        ],
        excluded_reference_ids=[
            UUID(str(x)) if not isinstance(x, UUID) else x
            for x in (row.excluded_reference_ids or [])
        ],
        identity_similarity=row.identity_similarity,
        brand_similarity=row.brand_similarity,
        user_accepted=row.user_accepted,
        review_notes=row.review_notes,
        parent_asset_id=getattr(row, "parent_asset_id", None),
        identity_profile_version=meta.get("identity_profile_version"),
        visual_consistency=meta.get("visual_consistency") or row.identity_similarity,
    )


@router.get("/readiness")
async def image_generation_readiness(
    current_user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    _ = current_user
    settings = get_settings()
    ready = DesignImageGenerationService(session, settings).readiness()
    from app.identity_generation.registry import get_provider_definition, serialize_registry_safe
    from app.identity_generation.errors import identity_error_message

    provider = get_provider_definition(settings)
    ready["identity_execution_mode"] = "person_identity_preservation"
    ready["identity_ab_harness_enabled"] = bool(settings.identity_ab_harness_enabled)
    ready["identity_max_images"] = int(settings.reference_identity_max_images)
    ready["subsystem"] = "identity_generation"
    ready["identity_provider"] = provider.provider_code
    ready["identity_capability_status"] = provider.capability_status.value
    ready["identity_provider_input_capacity"] = provider.maximum_identity_images
    ready["supports_supporting_references"] = provider.supports_supporting_references
    ready["paid_approval_required"] = provider.approval_required
    ready["identity_providers"] = serialize_registry_safe(settings)
    ready["identity_safe_summary"] = (
        identity_error_message("selected_but_not_transmitted")
        if not provider.supports_supporting_references
        and provider.supports_primary_reference
        else None
    )
    return ready


class IdentityAbHarnessBody(BaseModel):
    """Gated A/B harness — requires explicit paid-call confirmation."""

    reference_set_id: UUID
    prompt: str
    owner_confirmed_paid_calls: bool = False
    variants: list[str] | None = None  # A|B|C|D
    parent_asset_id: UUID | None = None


@router.post("/identity-ab-harness")
async def run_identity_ab_harness(
    body: IdentityAbHarnessBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> dict:
    """Controlled A/B comparison. Does not auto-run without owner confirm + flag."""
    settings = get_settings()
    if not bool(settings.identity_ab_harness_enabled):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "identity_ab_harness_disabled",
                "safe_message": "A/B harness отключён. Включите IDENTITY_AB_HARNESS_ENABLED.",
            },
        )
    if not body.owner_confirmed_paid_calls:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "owner_confirmation_required",
                "safe_message": "Подтвердите платные вызовы провайдера (owner_confirmed_paid_calls).",
            },
        )
    from uuid import uuid4

    from app.db.base import utc_now
    from app.db.models.user_request import UserRequestTable
    from app.schemas.contracts import UserRequestStatus
    from app.services.design_image_generation_service import (
        DesignImageGenerationService,
        ImageGenerationUnavailableError,
        apply_generation_success,
        apply_generation_unavailable,
    )

    variants = body.variants or ["A", "B", "C", "D"]
    allowed = {"A", "B", "C", "D"}
    variants = [v for v in variants if v in allowed][:4]
    if not variants:
        raise HTTPException(status_code=400, detail="invalid_variants")

    results: list[dict] = []
    service = DesignImageGenerationService(session, settings)
    for variant in variants:
        ur = UserRequestTable(
            id=uuid4(),
            owner_id=current_user.id,
            text=body.prompt[:4000],
            status=UserRequestStatus.COMPLETED,
            skill_code="design.image_generation",
            skill_version="1.0",
            skill_inputs={
                "reference_set_id": str(body.reference_set_id),
                "force_image_generation": "true",
                "execution_mode": "person_identity_preservation",
                "identity_fidelity": "maximum",
                "style_freedom": "low",
                "ab_variant": variant,
                "parent_asset_id": str(body.parent_asset_id) if body.parent_asset_id else "",
            },
            generated_visual_asset_ids=[],
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(ur)
        await session.commit()
        await session.refresh(ur)
        try:
            asset = await service.execute_for_user_request(
                ur,
                prompt=body.prompt,
                skill_inputs=dict(ur.skill_inputs or {}),
            )
            apply_generation_success(ur, asset)
            session.add(ur)
            session.add(asset)
            await session.commit()
            results.append(
                {
                    "variant": variant,
                    "user_request_id": str(ur.id),
                    "asset_id": str(asset.id),
                    "status": str(
                        asset.status.value if hasattr(asset.status, "value") else asset.status
                    ),
                    "parent_asset_id": str(asset.parent_asset_id)
                    if asset.parent_asset_id
                    else None,
                    "transmitted": (asset.generation_metadata or {}).get(
                        "transmitted_reference_ids"
                    ),
                    "mode": (asset.generation_metadata or {}).get("actual_mode"),
                }
            )
        except ImageGenerationUnavailableError as exc:
            apply_generation_unavailable(
                ur, message=exc.user_message, category=exc.category
            )
            session.add(ur)
            await session.commit()
            results.append(
                {
                    "variant": variant,
                    "user_request_id": str(ur.id),
                    "asset_id": None,
                    "error": exc.category,
                    "message": exc.user_message,
                }
            )

    return {
        "harness": "identity_ab",
        "provider_capability": "unknown",
        "note": (
            "Owner visual review required. Do not mark suitable_for_identity "
            "without recognizable likeness."
        ),
        "results": results,
    }


@router.get("", response_model=list[GeneratedVisualAsset])
async def list_generated_visuals(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = 100,
) -> list[GeneratedVisualAsset]:
    stmt = (
        select(GeneratedVisualAssetTable)
        .where(GeneratedVisualAssetTable.owner_id == current_user.id)
        .order_by(GeneratedVisualAssetTable.created_at.desc())
        .limit(min(max(limit, 1), 200))
    )
    result = await session.execute(stmt)
    return [_to_contract(r) for r in result.scalars().all()]


@router.get("/{asset_id}", response_model=GeneratedVisualAsset)
async def get_generated_visual(
    asset_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> GeneratedVisualAsset:
    row = await session.get(GeneratedVisualAssetTable, asset_id)
    if row is None or not _asset_visible_to_user(row, current_user, asset_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    return _to_contract(row)


@router.get("/{asset_id}/content")
async def get_generated_visual_content(
    asset_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> FileResponse:
    row = await session.get(GeneratedVisualAssetTable, asset_id)
    if row is None or not _asset_visible_to_user(row, current_user, asset_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    if not row.content_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="content_unavailable")
    path = Path(row.content_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="content_unavailable")
    return FileResponse(path, media_type=row.mime_type or "image/png", filename=f"{asset_id}.png")


class VisualReviewBody(BaseModel):
    identity_similarity: str | None = None
    brand_similarity: str | None = None
    user_accepted: bool | None = None
    review_notes: str | None = None
    rejection_code: str | None = None  # rejected_insufficient_similarity


@router.post("/{asset_id}/review", response_model=GeneratedVisualAsset)
async def review_generated_visual(
    asset_id: UUID,
    body: VisualReviewBody,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> GeneratedVisualAsset:
    from app.schemas.contracts import GeneratedVisualAssetStatus

    row = await session.get(GeneratedVisualAssetTable, asset_id)
    if row is None or not _asset_visible_to_user(row, current_user, asset_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
    # Immutable freeze: already owner-rejected assets cannot be overwritten to accepted.
    if row.status == GeneratedVisualAssetStatus.REJECTED_INSUFFICIENT_SIMILARITY and (
        body.user_accepted is True
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "asset_immutable",
                "safe_message": "Отклонённый результат сохранён и не перезаписывается.",
            },
        )
    allowed = {"high", "medium", "low", "not_applicable", None}
    if body.identity_similarity not in allowed or body.brand_similarity not in allowed:
        raise HTTPException(status_code=400, detail="invalid_similarity")
    if body.identity_similarity is not None:
        row.identity_similarity = body.identity_similarity
    if body.brand_similarity is not None:
        row.brand_similarity = body.brand_similarity
    if body.user_accepted is not None:
        row.user_accepted = body.user_accepted
    if body.review_notes is not None:
        row.review_notes = body.review_notes[:2000]
    rejection = (body.rejection_code or "").strip()
    if rejection == "rejected_insufficient_similarity" or (
        body.user_accepted is False and body.identity_similarity == "low"
    ):
        row.status = GeneratedVisualAssetStatus.REJECTED_INSUFFICIENT_SIMILARITY
        row.user_accepted = False
        row.review_notes = (row.review_notes or "rejected_insufficient_similarity")[:2000]
        meta = dict(row.generation_metadata or {})
        meta["owner_rejection"] = "rejected_insufficient_similarity"
        meta["immutable_failed_result"] = True
        row.generation_metadata = meta
    elif body.user_accepted is True:
        row.status = GeneratedVisualAssetStatus.SUCCEEDED
        row.user_accepted = True
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_contract(row)
