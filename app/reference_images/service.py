"""Reference image upload, quality, and selection (Phase H2.6A-R)."""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.base import utc_now
from app.db.models.reference_visual import ReferenceSetTable, ReferenceVisualAssetTable
from app.schemas.contracts import (
    ReferenceAssetPurpose,
    ReferenceQualityStatus,
    ReferenceSafetyStatus,
    ReferenceSelectionResult,
    ReferenceSetStatus,
    ReferenceSubjectType,
    ReferenceVisualAsset,
)

_ALLOWED_MIME = frozenset({"image/png", "image/jpeg", "image/webp"})
_MIME_BY_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


def _safe_filename(name: str) -> str:
    base = Path(name or "image").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "image"
    return cleaned[:180]


def _sniff_mime(payload: bytes) -> str | None:
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    status: ReferenceQualityStatus
    notes: str


def assess_reference_quality(
    *,
    width: int,
    height: int,
    byte_size: int,
    purpose: ReferenceAssetPurpose,
    subject_type: ReferenceSubjectType,
    min_w: int,
    min_h: int,
) -> QualityAssessment:
    notes: list[str] = []
    if width < min_w or height < min_h:
        return QualityAssessment(
            ReferenceQualityStatus.UNSUITABLE,
            f"Разрешение слишком низкое ({width}×{height}). Минимум {min_w}×{min_h}.",
        )
    if width < min_w * 2 or height < min_h * 2:
        notes.append("Разрешение ограниченное — добавьте более детальный кадр.")
    pixels = width * height
    density = byte_size / max(pixels, 1)
    if density < 0.02:
        notes.append("Изображение выглядит чрезмерно сжатым.")
    if subject_type == ReferenceSubjectType.PERSON and purpose in {
        ReferenceAssetPurpose.FACE_REFERENCE,
        ReferenceAssetPurpose.IDENTITY_REFERENCE,
    }:
        if width < 512 or height < 512:
            notes.append("Для лица желательно ≥512×512 и хороший анфас.")
    if notes:
        return QualityAssessment(ReferenceQualityStatus.LIMITED, " ".join(notes))
    return QualityAssessment(ReferenceQualityStatus.SUITABLE, "Подходит как референс.")


class ReferenceUploadError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ReferenceImageService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    def _to_asset_contract(
        self,
        row: ReferenceVisualAssetTable,
        *,
        attach_status: str | None = None,
        attach_message: str | None = None,
    ) -> ReferenceVisualAsset:
        return ReferenceVisualAsset(
            id=row.id,
            owner_id=row.owner_id,
            project_id=row.project_id,
            user_request_id=row.user_request_id,
            original_filename=row.original_filename,
            mime_type=row.mime_type,
            width=row.width,
            height=row.height,
            byte_size=row.byte_size,
            checksum=row.checksum,
            storage_uri=row.storage_uri,
            asset_purpose=row.asset_purpose,
            subject_type=row.subject_type,
            quality_status=row.quality_status,
            quality_notes=row.quality_notes,
            safety_status=row.safety_status,
            created_at=row.created_at,
            archived_at=row.archived_at,
            attach_status=attach_status,
            attach_message=attach_message,
            asset_purposes=[str(x) for x in (getattr(row, "asset_purposes", None) or [])],
        )

    async def _attach_existing_to_set(
        self,
        *,
        owner_id: UUID,
        existing: ReferenceVisualAssetTable,
        set_id: UUID | None,
    ) -> ReferenceVisualAsset:
        """Idempotent attach of an existing owner asset to a ReferenceSet."""
        if set_id is None:
            return self._to_asset_contract(
                existing,
                attach_status="reused_existing_asset",
                attach_message="Файл уже был загружен и использован повторно.",
            )
        ref_set = await self._session.get(ReferenceSetTable, set_id)
        if ref_set is None or ref_set.owner_id != owner_id:
            raise ReferenceUploadError("set_not_found", "Reference Set не найден.")
        ids = [str(x) for x in (ref_set.reference_asset_ids or [])]
        if str(existing.id) in ids:
            return self._to_asset_contract(
                existing,
                attach_status="already_attached",
                attach_message="Этот референс уже добавлен.",
            )
        settings = self._settings
        if len(ids) >= settings.reference_image_max_count:
            raise ReferenceUploadError(
                "set_full",
                f"В наборе уже {settings.reference_image_max_count} изображений.",
            )
        ids.append(str(existing.id))
        ref_set.reference_asset_ids = ids
        if ref_set.primary_reference_id is None:
            ref_set.primary_reference_id = existing.id
        if ref_set.status == ReferenceSetStatus.DRAFT:
            ref_set.status = ReferenceSetStatus.READY
        ref_set.updated_at = utc_now()
        self._session.add(ref_set)
        await self._session.commit()
        return self._to_asset_contract(
            existing,
            attach_status="reused_existing_asset",
            attach_message="Файл уже был загружен и использован повторно.",
        )

    async def upload(
        self,
        *,
        owner_id: UUID,
        payload: bytes,
        filename: str,
        declared_mime: str | None,
        asset_purpose: ReferenceAssetPurpose,
        subject_type: ReferenceSubjectType,
        user_request_id: UUID | None = None,
        project_id: UUID | None = None,
        set_id: UUID | None = None,
        consent_confirmed: bool = False,
    ) -> ReferenceVisualAsset:
        if not consent_confirmed and subject_type == ReferenceSubjectType.PERSON:
            raise ReferenceUploadError(
                "consent_required",
                "Подтвердите право использовать изображения человека перед загрузкой.",
            )
        settings = self._settings
        if len(payload) == 0:
            raise ReferenceUploadError("empty_file", "Пустой файл отклонён.")
        if len(payload) > settings.reference_image_max_bytes_per_file:
            raise ReferenceUploadError(
                "file_too_large",
                f"Файл превышает лимит {settings.reference_image_max_bytes_per_file} байт.",
            )
        mime = _sniff_mime(payload)
        if mime is None or mime not in _ALLOWED_MIME:
            raise ReferenceUploadError(
                "unsupported_mime",
                "Допустимы только PNG, JPEG и WebP.",
            )
        if declared_mime and declared_mime.split(";")[0].strip().lower() not in _ALLOWED_MIME:
            raise ReferenceUploadError("unsupported_mime", "MIME не поддерживается.")

        try:
            with Image.open(io.BytesIO(payload)) as img:
                img = ImageOps.exif_transpose(img)
                # Drop EXIF by re-encoding without metadata
                width, height = img.size
                if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
                    raise ReferenceUploadError(
                        "animated_not_supported",
                        "Анимированные изображения пока не поддерживаются.",
                    )
                out = io.BytesIO()
                fmt = "PNG" if mime == "image/png" else "JPEG" if mime == "image/jpeg" else "WEBP"
                save_img = img.convert("RGB") if fmt in {"JPEG", "WEBP"} else img.convert("RGBA")
                save_kwargs = {"format": fmt}
                if fmt == "JPEG":
                    save_kwargs["quality"] = 92
                    save_kwargs["optimize"] = True
                save_img.save(out, **save_kwargs)
                clean_bytes = out.getvalue()
        except ReferenceUploadError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ReferenceUploadError("corrupt_image", "Не удалось декодировать изображение.") from exc

        if width < settings.reference_image_min_width or height < settings.reference_image_min_height:
            raise ReferenceUploadError(
                "dimensions_too_small",
                f"Минимум {settings.reference_image_min_width}×{settings.reference_image_min_height}.",
            )

        checksum = "sha256:" + hashlib.sha256(clean_bytes).hexdigest()
        # Idempotent reuse within owner — never expose raw duplicate_checksum to UI.
        existing_result = await self._session.execute(
            select(ReferenceVisualAssetTable).where(
                ReferenceVisualAssetTable.owner_id == owner_id,
                ReferenceVisualAssetTable.checksum == checksum,
                ReferenceVisualAssetTable.archived_at.is_(None),
            )
        )
        existing_row = existing_result.scalar_one_or_none()
        if existing_row is not None:
            return await self._attach_existing_to_set(
                owner_id=owner_id,
                existing=existing_row,
                set_id=set_id,
            )

        if set_id is not None:
            ref_set = await self._session.get(ReferenceSetTable, set_id)
            if ref_set is None or ref_set.owner_id != owner_id:
                raise ReferenceUploadError("set_not_found", "Reference Set не найден.")
            ids = [str(x) for x in (ref_set.reference_asset_ids or [])]
            if len(ids) >= settings.reference_image_max_count:
                raise ReferenceUploadError(
                    "set_full",
                    f"В наборе уже {settings.reference_image_max_count} изображений.",
                )
            # total bytes across set
            total = len(clean_bytes)
            for aid in ids:
                row = await self._session.get(ReferenceVisualAssetTable, UUID(str(aid)))
                if row and row.owner_id == owner_id:
                    total += int(row.byte_size or 0)
            if total > settings.reference_image_max_total_bytes:
                raise ReferenceUploadError(
                    "set_total_too_large",
                    "Суммарный размер референсов превышает лимит.",
                )

        quality = assess_reference_quality(
            width=width,
            height=height,
            byte_size=len(clean_bytes),
            purpose=asset_purpose,
            subject_type=subject_type,
            min_w=settings.reference_image_min_width,
            min_h=settings.reference_image_min_height,
        )

        asset_id = uuid4()
        ext = { "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[mime]
        storage_root = Path(settings.reference_image_storage_dir) / str(owner_id)
        storage_root.mkdir(parents=True, exist_ok=True)
        path = storage_root / f"{asset_id}{ext}"
        path.write_bytes(clean_bytes)

        row = ReferenceVisualAssetTable(
            id=asset_id,
            owner_id=owner_id,
            project_id=project_id,
            user_request_id=user_request_id,
            original_filename=_safe_filename(filename)[:255],
            mime_type=mime,
            width=width,
            height=height,
            byte_size=len(clean_bytes),
            checksum=checksum,
            storage_uri=f"/reference-visual-assets/{asset_id}/content",
            content_path=str(path.as_posix()),
            asset_purpose=asset_purpose,
            asset_purposes=[asset_purpose.value],
            subject_type=subject_type,
            quality_status=quality.status,
            quality_notes=quality.notes[:1000],
            safety_status=ReferenceSafetyStatus.PASSED,
            created_at=utc_now(),
        )
        self._session.add(row)

        if set_id is not None:
            ref_set = await self._session.get(ReferenceSetTable, set_id)
            assert ref_set is not None
            ids = [str(x) for x in (ref_set.reference_asset_ids or [])]
            ids.append(str(asset_id))
            ref_set.reference_asset_ids = ids
            if ref_set.primary_reference_id is None:
                ref_set.primary_reference_id = asset_id
            ref_set.updated_at = utc_now()
            if len(ids) >= 1 and ref_set.status == ReferenceSetStatus.DRAFT:
                ref_set.status = ReferenceSetStatus.READY
            self._session.add(ref_set)

        await self._session.commit()
        await self._session.refresh(row)
        return self._to_asset_contract(
            row,
            attach_status="created",
            attach_message=None,
        )

    async def create_set(
        self,
        *,
        owner_id: UUID,
        title: str,
        subject_type: ReferenceSubjectType,
        user_request_id: UUID | None = None,
        project_id: UUID | None = None,
        identity_notes: str | None = None,
        immutable_traits: list[str] | None = None,
        allowed_variations: list[str] | None = None,
        forbidden_changes: list[str] | None = None,
        consent_confirmed: bool = False,
    ) -> ReferenceSetTable:
        row = ReferenceSetTable(
            id=uuid4(),
            owner_id=owner_id,
            project_id=project_id,
            user_request_id=user_request_id,
            title=(title or "Reference set")[:255],
            subject_type=subject_type,
            preservation_goal="maximize_recognizability",
            status=ReferenceSetStatus.DRAFT,
            reference_asset_ids=[],
            primary_reference_id=None,
            identity_notes=(identity_notes or None),
            immutable_traits=list(immutable_traits or []),
            allowed_variations=list(allowed_variations or []),
            forbidden_changes=list(forbidden_changes or []),
            consent_confirmed=bool(consent_confirmed),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def select_for_provider(
        self,
        *,
        owner_id: UUID,
        set_id: UUID,
    ) -> ReferenceSelectionResult:
        settings = self._settings
        ref_set = await self._session.get(ReferenceSetTable, set_id)
        if ref_set is None or ref_set.owner_id != owner_id:
            raise ReferenceUploadError("set_not_found", "Reference Set не найден.")
        ids = [UUID(str(x)) for x in (ref_set.reference_asset_ids or [])]
        assets: list[ReferenceVisualAssetTable] = []
        for aid in ids:
            row = await self._session.get(ReferenceVisualAssetTable, aid)
            if row and row.owner_id == owner_id and row.archived_at is None:
                assets.append(row)

        from app.domain.reference_selection import select_person_identity_refs, views_from_rows

        if ref_set.subject_type == ReferenceSubjectType.PERSON:
            identity_max = max(1, min(int(settings.reference_identity_max_images), 5))
            return select_person_identity_refs(
                assets=views_from_rows(assets),
                primary_reference_id=ref_set.primary_reference_id,
                subject_type=ref_set.subject_type,
                identity_max=identity_max,
                style_max=1,
                appearance_max=1,
            )

        # Non-person: keep ranked subset with provider cap (not identity mode).
        max_n = max(1, min(int(settings.reference_provider_max_images), 15))

        def rank(a: ReferenceVisualAssetTable) -> tuple[int, int, int]:
            purpose_rank = {
                ReferenceAssetPurpose.FACE_FRONT: 0,
                ReferenceAssetPurpose.FACE_REFERENCE: 0,
                ReferenceAssetPurpose.IDENTITY_REFERENCE: 1,
                ReferenceAssetPurpose.FACE_THREE_QUARTER: 1,
                ReferenceAssetPurpose.FACE_PROFILE: 2,
                ReferenceAssetPurpose.FACE_CLOSEUP: 2,
                ReferenceAssetPurpose.LOGO_REFERENCE: 0,
                ReferenceAssetPurpose.PRODUCT_REFERENCE: 1,
                ReferenceAssetPurpose.BRAND_REFERENCE: 2,
                ReferenceAssetPurpose.BODY_REFERENCE: 3,
                ReferenceAssetPurpose.HALF_BODY: 3,
                ReferenceAssetPurpose.FULL_BODY: 3,
                ReferenceAssetPurpose.POSE_REFERENCE: 3,
                ReferenceAssetPurpose.POSE: 3,
                ReferenceAssetPurpose.OUTFIT_REFERENCE: 4,
                ReferenceAssetPurpose.CLOTHING: 4,
                ReferenceAssetPurpose.HAIR: 4,
                ReferenceAssetPurpose.COMPOSITION_REFERENCE: 5,
                ReferenceAssetPurpose.STYLE_REFERENCE: 6,
                ReferenceAssetPurpose.BACKGROUND_REFERENCE: 7,
                ReferenceAssetPurpose.OTHER: 8,
            }.get(a.asset_purpose, 9)
            quality_rank = {
                ReferenceQualityStatus.SUITABLE: 0,
                ReferenceQualityStatus.LIMITED: 1,
                ReferenceQualityStatus.PENDING: 2,
                ReferenceQualityStatus.UNSUITABLE: 9,
            }.get(a.quality_status, 5)
            area = -((a.width or 0) * (a.height or 0))
            primary_boost = -100 if ref_set.primary_reference_id == a.id else 0
            return (primary_boost + purpose_rank, quality_rank, area)

        ranked = sorted(assets, key=rank)
        selected = [a for a in ranked if a.quality_status != ReferenceQualityStatus.UNSUITABLE][:max_n]
        selected_ids = [a.id for a in selected]
        excluded = [a for a in assets if a.id not in set(selected_ids)]
        reasons: dict[str, str] = {}
        for a in excluded:
            if a.quality_status == ReferenceQualityStatus.UNSUITABLE:
                reasons[str(a.id)] = "unsuitable_quality"
            elif len(selected_ids) >= max_n:
                reasons[str(a.id)] = "provider_limit"
            else:
                reasons[str(a.id)] = "not_selected"
        summary = f"Загружено: {len(assets)}. Выбрано: {len(selected_ids)}. Не использовано: {len(excluded)}."
        return ReferenceSelectionResult(
            selected_reference_ids=selected_ids,
            excluded_reference_ids=[a.id for a in excluded],
            exclusion_reasons=reasons,
            max_provider_references=max_n,
            selection_summary=summary,
            identity_selected_ids=[],
            appearance_selected_ids=[],
            scene_selected_ids=selected_ids,
            identity_selected_count=0,
            style_selected_count=len(selected_ids),
            excluded_count=len(excluded),
            stored_count=len(assets),
            transmitted_reference_ids=selected_ids[:1],
            primary_reference_id=ref_set.primary_reference_id
            if ref_set.primary_reference_id in selected_ids
            else (selected_ids[0] if selected_ids else None),
        )

    async def update_asset_purposes(
        self,
        *,
        owner_id: UUID,
        asset_id: UUID,
        asset_purpose: ReferenceAssetPurpose,
        asset_purposes: list[str] | None = None,
    ) -> ReferenceVisualAsset:
        row = await self._session.get(ReferenceVisualAssetTable, asset_id)
        if row is None or row.owner_id != owner_id or row.archived_at is not None:
            raise ReferenceUploadError("asset_not_found", "Референс не найден.")
        purposes = list(asset_purposes or [])
        if not purposes:
            purposes = [asset_purpose.value]
        elif asset_purpose.value not in purposes:
            purposes = [asset_purpose.value, *purposes]
        # Deduplicate preserving order
        seen: set[str] = set()
        cleaned: list[str] = []
        for p in purposes:
            if p not in seen:
                seen.add(p)
                cleaned.append(p)
        row.asset_purpose = asset_purpose
        row.asset_purposes = cleaned[:8]
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_asset_contract(row)
