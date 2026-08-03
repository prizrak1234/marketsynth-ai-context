"""VS.2A commercial vertical slice — preview → approval → single clip → asset."""

from __future__ import annotations

import copy
import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.video_clip_request import VideoClipRequestTable
from app.media_generation.gateway import (
    GatewayCreateRequest,
    GatewayInvokeStatus,
    GatewayModality,
    GatewayPollResult,
)
from app.media_generation.safe_metadata import sanitize_generation_metadata
from app.media_generation.scene_graph import VideoSceneMode, build_single_clip_scene_graph
from app.media_generation.signed_asset_urls import SignedUrlError, mint_generated_visual_asset_url
from app.media_generation.video_clip_download import (
    VideoDownloadError,
    download_provider_video_to_temp,
    finalize_video_temp_file,
)
from app.media_generation.video_duration_probe import (
    VideoDurationProbeError,
    classify_duration_validation,
    probe_mp4_duration_seconds,
)
from app.media_generation.video_owner_acceptance_preview import (
    CANONICAL_CLIP_REQUEST_ID,
    CANONICAL_RESULT_ASSET_ID,
    CANONICAL_SOURCE_IMAGE_ASSET_ID,
)
from app.media_generation.video_readiness import image_to_video_live_verified, write_smoke_success
from app.media_generation.video_router import build_video_router
from app.schemas.contracts import (
    DurationValidationStatus,
    GeneratedVisualAssetStatus,
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    SpecialistSkillCode,
    VideoClipExecutionPublic,
    VideoClipHydrationPublic,
    VideoClipPreviewPublic,
    VideoClipRequestStatus,
    VideoOwnerAcceptancePreviewPublic,
)
from app.video_studio.camera_movements import build_motion_prompt, resolve_camera_movement
from app.video_studio.contracts import (
    VideoDurationMode,
    duration_mode_for,
    validate_aspect_ratio,
    validate_requested_duration,
)
from app.video_studio.provider_duration_capabilities import (
    assert_single_clip_duration_supported,
    provider_payload_duration_seconds,
    provider_reported_duration_seconds,
)

_OUTCOME_UNKNOWN_POLL_CODES = frozenset(
    {
        "gptunnel_poll_timeout",
        "poll_network_error",
        "provider_status_unavailable",
    }
)
_OUTCOME_UNKNOWN_DOWNLOAD_CODES = frozenset(
    {
        "result_download_timeout",
        "result_download_failed",
        "result_download_too_large",
        "asset_persist_failed",
    }
)

_OWNER_MESSAGE_OUTCOME_UNKNOWN = (
    "Статус видео пока не подтверждён. Повторный запуск может привести к повторному списанию."
)
_OWNER_MESSAGE_DOWNLOAD_FAILED = (
    "Видео создано провайдером, но не удалось сохранить файл."
)
_OWNER_MESSAGE_SOURCE_PUBLIC = "Стартовое изображение недоступно генератору."
_OWNER_MESSAGE_FILE_TOO_LARGE = "Полученный видеофайл превышает допустимый размер."
_OWNER_MESSAGE_DURATION_MISMATCH = (
    "Видео создано, но фактическая длительность отличается от выбранной. "
    "Проверьте результат перед использованием."
)


def _request_hash(
    *,
    source_image_asset_id: UUID,
    motion_brief: str,
    duration_seconds: int,
    aspect_ratio: str,
) -> str:
    payload = f"{source_image_asset_id}|{motion_brief.strip()}|{duration_seconds}|{aspect_ratio}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cost_label(units: str | None) -> str:
    if not units:
        return "уточняется перед созданием"
    return f"≈ {units} ед. (по каталогу)"


def _owner_message_for_error_code(code: str | None, fallback: str | None = None) -> str:
    if code in _OUTCOME_UNKNOWN_DOWNLOAD_CODES or code == "result_download_too_large":
        if code == "result_download_too_large":
            return _OWNER_MESSAGE_FILE_TOO_LARGE
        return _OWNER_MESSAGE_DOWNLOAD_FAILED
    if code in {"start_frame_signed_url_failed", "public_backend_missing", "disabled"}:
        return _OWNER_MESSAGE_SOURCE_PUBLIC
    return fallback or "Не удалось создать клип."


class VideoClipCommercialService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._router = build_video_router(settings)

    async def _load_source_asset(self, owner_id: UUID, asset_id: UUID) -> GeneratedVisualAssetTable:
        row = await self._session.get(GeneratedVisualAssetTable, asset_id)
        if row is None or row.owner_id != owner_id:
            raise InvalidStateError("source_asset_not_found")
        if row.asset_type == GeneratedVisualAssetType.IDENTITY_AB_CHILD:
            raise InvalidStateError("source_asset_identity_reference_blocked")
        if row.status != GeneratedVisualAssetStatus.SUCCEEDED:
            raise InvalidStateError("source_asset_not_ready")
        if row.user_accepted is not True:
            raise InvalidStateError("source_asset_not_accepted")
        if not row.content_path or not Path(row.content_path).is_file():
            raise InvalidStateError("source_asset_file_missing")
        if not (row.mime_type or "").startswith("image/"):
            raise InvalidStateError("source_asset_not_image")
        return row

    async def create_preview(
        self,
        *,
        owner_id: UUID,
        source_image_asset_id: UUID,
        motion_brief: str,
        duration_seconds: int,
        aspect_ratio: str,
        project_id: UUID | None = None,
        user_request_id: UUID | None = None,
        camera_movement_id: str | None = None,
        camera_movement_instruction: str | None = None,
    ) -> VideoClipPreviewPublic:
        seconds = validate_requested_duration(duration_seconds)
        if duration_mode_for(seconds) != VideoDurationMode.SINGLE_CLIP:
            raise InvalidStateError("long_form_requires_plan_preview")
        assert_single_clip_duration_supported(seconds, self._settings.gptunnel_video_model)
        validate_aspect_ratio(aspect_ratio)
        if camera_movement_id:
            resolve_camera_movement(camera_movement_id)
            motion_brief = build_motion_prompt(
                movement_id=camera_movement_id,
                instruction=camera_movement_instruction,
                scene_description=motion_brief,
            )
        source = await self._load_source_asset(owner_id, source_image_asset_id)
        req_hash = _request_hash(
            source_image_asset_id=source_image_asset_id,
            motion_brief=motion_brief,
            duration_seconds=seconds,
            aspect_ratio=aspect_ratio,
        )
        graph = build_single_clip_scene_graph(
            brief=motion_brief,
            mode=VideoSceneMode.IMAGE_TO_VIDEO,
            duration_seconds=seconds,
            aspect_ratio=aspect_ratio,
        )
        graph.scenes[0].start_frame_asset_id = str(source_image_asset_id)
        quotes = self._router.quote(modality=GatewayModality.VIDEO)
        recommended = next((q for q in quotes.quotes if q.recommended), None)
        estimated = recommended.estimated_cost_units if recommended else None
        ready = self._router.any_connected and image_to_video_live_verified(self._settings)
        blocked: str | None = None
        if not self._router.any_connected:
            blocked = "Генерация видео пока недоступна. Видеодвижок ещё не подключён."
        elif not image_to_video_live_verified(self._settings):
            blocked = (
                "Генерация видео пока недоступна. "
                "Функция будет активирована после проверки видеодвижка."
            )
        preview_snapshot = {
            "recommendation": quotes.recommendation_display_name,
            "recommendation_reason_ru": quotes.recommendation_reason_ru,
            "quotes": [
                {
                    "display_name": q.display_name,
                    "estimated_cost_units": q.estimated_cost_units,
                    "connected": q.connected,
                    "recommended": q.recommended,
                }
                for q in quotes.quotes
            ],
        }
        row = VideoClipRequestTable(
            owner_id=owner_id,
            project_id=project_id,
            user_request_id=user_request_id or source.user_request_id,
            source_image_asset_id=source_image_asset_id,
            motion_brief=motion_brief.strip(),
            duration_seconds=seconds,
            aspect_ratio=aspect_ratio,
            request_hash=req_hash,
            preview_snapshot_json=preview_snapshot,
            estimated_cost_units=estimated,
            quote_at=utc_now(),
            status=VideoClipRequestStatus.PREVIEW,
            scene_graph_json=graph.to_safe_dict(),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        limitations = [
            "Движение зависит от описания и возможностей видеодвижка.",
            "Итог нужно визуально принять перед использованием в рекламе.",
        ]
        provider_durations = provider_reported_duration_seconds(
            self._settings.gptunnel_video_model
        )
        if provider_durations is not None and provider_durations != seconds:
            limitations.append(
                f"Текущий видеодвижок создаёт клипы длительностью {provider_durations} с."
            )
        return VideoClipPreviewPublic(
            clip_request_id=row.id,
            status=row.status,
            motion_brief=row.motion_brief,
            duration_seconds=row.duration_seconds,
            aspect_ratio=row.aspect_ratio,
            estimated_cost_label=_cost_label(row.estimated_cost_units),
            estimated_wait_seconds=90,
            what_will_be_created_ru=(
                f"Короткий клип {seconds} с ({aspect_ratio}) на основе вашего изображения."
            ),
            limitations_ru=limitations,
            ready_to_generate=ready,
            blocked_reason_ru=blocked,
        )

    async def _find_idempotent(
        self, owner_id: UUID, idempotency_key: str
    ) -> VideoClipRequestTable | None:
        stmt = select(VideoClipRequestTable).where(
            VideoClipRequestTable.owner_id == owner_id,
            VideoClipRequestTable.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_approved(
        self,
        *,
        owner_id: UUID,
        clip_request_id: UUID,
        idempotency_key: str,
        approved: bool,
    ) -> VideoClipExecutionPublic:
        if not approved:
            raise InvalidStateError("approval_required")
        if not idempotency_key.strip():
            raise InvalidStateError("idempotency_key_required")

        existing = await self._find_idempotent(owner_id, idempotency_key.strip())
        if existing is not None:
            if existing.id != clip_request_id:
                raise InvalidStateError("idempotency_key_conflict")
            return self._to_execution_public(existing)

        row = await self._session.get(VideoClipRequestTable, clip_request_id)
        if row is None or row.owner_id != owner_id:
            raise InvalidStateError("clip_request_not_found")
        if duration_mode_for(row.duration_seconds) != VideoDurationMode.SINGLE_CLIP:
            raise InvalidStateError("long_form_requires_plan_preview")
        assert_single_clip_duration_supported(
            row.duration_seconds, self._settings.gptunnel_video_model
        )
        if row.status != VideoClipRequestStatus.PREVIEW:
            raise InvalidStateError("clip_request_not_in_preview")
        if not image_to_video_live_verified(self._settings):
            bootstrap_ok = (
                self._settings.video_generation_enabled and self._router.any_connected
            )
            if not bootstrap_ok:
                raise InvalidStateError("video_not_ready")

        row.idempotency_key = idempotency_key.strip()
        row.approved_at = utc_now()
        row.approved_request_hash = row.request_hash
        row.status = VideoClipRequestStatus.EXECUTING
        await self._session.commit()

        source = await self._load_source_asset(owner_id, row.source_image_asset_id)
        started = time.monotonic()
        evidence: dict[str, Any] = {
            "quote_at": row.quote_at.isoformat() if row.quote_at else None,
            "estimated_cost_units": row.estimated_cost_units,
            "currency": "catalog_units",
        }

        try:
            grant = await mint_generated_visual_asset_url(
                self._settings,
                asset_id=source.id,
                content_path=str(source.content_path),
                ttl_seconds=600,
            )
        except SignedUrlError as exc:
            await self._mark_failed(
                row,
                error_code=exc.code,
                owner_message=_OWNER_MESSAGE_SOURCE_PUBLIC,
                evidence=evidence,
            )
            raise InvalidStateError("start_frame_signed_url_failed") from exc

        request = GatewayCreateRequest(
            modality=GatewayModality.VIDEO,
            model=self._settings.gptunnel_video_model,
            prompt=row.motion_brief[:4000],
            aspect_ratio=row.aspect_ratio,
            images=[grant.absolute_url],
            duration_seconds=row.duration_seconds,
            metadata={"clip_request_id": str(row.id), "mode": "image_to_video"},
        )
        model = self._settings.gptunnel_video_model
        evidence["requested_duration_seconds"] = row.duration_seconds
        evidence["provider_payload_duration"] = provider_payload_duration_seconds(model)
        evidence["provider_reported_duration"] = provider_reported_duration_seconds(model)
        try:
            provider_code, created = await self._router.create(request)
        except (httpx.HTTPError, OSError) as exc:
            await self._mark_outcome_unknown(
                row,
                error_code="provider_status_unavailable",
                evidence={**evidence, "create_error": type(exc).__name__},
            )
            return self._to_execution_public(row)

        evidence["provider_code"] = provider_code
        evidence["model"] = self._settings.gptunnel_video_model
        row.provider_code = provider_code

        if created.status != GatewayInvokeStatus.QUEUED or not created.job_id:
            await self._mark_failed(
                row,
                error_code=created.detail_code or "create_failed",
                owner_message="Не удалось запустить создание видео. Попробуйте позже.",
                evidence=evidence,
            )
            return self._to_execution_public(row)

        row.provider_job_id = created.job_id
        evidence["provider_job_id"] = created.job_id
        evidence["paid_call_performed"] = bool(created.paid_call_performed)
        await self._session.commit()

        try:
            polled = await self._router.poll(provider_code, created.job_id)
        except (httpx.HTTPError, OSError) as exc:
            evidence["latency_ms"] = int((time.monotonic() - started) * 1000)
            evidence["poll_error"] = type(exc).__name__
            await self._mark_outcome_unknown(
                row,
                error_code="poll_network_error",
                evidence=evidence,
            )
            return self._to_execution_public(row)

        evidence["latency_ms"] = int((time.monotonic() - started) * 1000)
        evidence["poll_status"] = polled.status.value
        evidence["paid_call_performed"] = bool(
            evidence.get("paid_call_performed") or polled.paid_call_performed
        )
        return await self._finalize_from_poll(
            row,
            owner_id=owner_id,
            source=source,
            provider_code=provider_code,
            polled=polled,
            evidence=evidence,
        )

    async def reconcile(
        self,
        *,
        owner_id: UUID,
        clip_request_id: UUID,
    ) -> VideoClipExecutionPublic:
        row = await self._session.get(VideoClipRequestTable, clip_request_id)
        if row is None or row.owner_id != owner_id:
            raise InvalidStateError("clip_request_not_found")
        if row.status not in {
            VideoClipRequestStatus.EXECUTING,
            VideoClipRequestStatus.OUTCOME_UNKNOWN,
        }:
            raise InvalidStateError("clip_request_not_reconcilable")
        if not row.provider_job_id or not row.provider_code:
            raise InvalidStateError("reconcile_requires_provider_job_id")

        source = await self._load_source_asset(owner_id, row.source_image_asset_id)
        evidence = dict(row.execution_evidence_json or {})
        evidence["reconcile_at"] = datetime.now(UTC).isoformat()

        try:
            polled = await self._router.poll(row.provider_code, row.provider_job_id)
        except (httpx.HTTPError, OSError) as exc:
            evidence["poll_error"] = type(exc).__name__
            await self._mark_outcome_unknown(
                row,
                error_code="poll_network_error",
                evidence=evidence,
            )
            return self._to_execution_public(row)

        evidence["poll_status"] = polled.status.value
        return await self._finalize_from_poll(
            row,
            owner_id=owner_id,
            source=source,
            provider_code=row.provider_code,
            polled=polled,
            evidence=evidence,
        )

    async def _finalize_from_poll(
        self,
        row: VideoClipRequestTable,
        *,
        owner_id: UUID,
        source: GeneratedVisualAssetTable,
        provider_code: str,
        polled: GatewayPollResult,
        evidence: dict[str, Any],
    ) -> VideoClipExecutionPublic:
        if polled.status != GatewayInvokeStatus.DONE or not polled.url:
            detail = polled.detail_code or "poll_failed"
            if detail in _OUTCOME_UNKNOWN_POLL_CODES or (
                row.provider_job_id and detail == "gptunnel_poll_timeout"
            ):
                await self._mark_outcome_unknown(row, error_code=detail, evidence=evidence)
            else:
                await self._mark_failed(
                    row,
                    error_code=detail,
                    owner_message=(
                        "Создание видео не завершилось. Если списание произошло, "
                        "обратитесь в поддержку с номером запроса."
                    ),
                    evidence=evidence,
                )
            return self._to_execution_public(row)

        temp_path: Path | None = None
        try:
            downloaded = await download_provider_video_to_temp(
                self._settings,
                url=polled.url,
                mime_hint=polled.mime,
            )
            temp_path = downloaded.temp_path
            asset_id = uuid4()
            storage_dir = Path(self._settings.image_generation_storage_dir)
            file_path = finalize_video_temp_file(temp_path, storage_dir, str(asset_id))
            temp_path = None

            requested_duration = row.duration_seconds
            duration_evidence: dict[str, Any] = {
                "requested_duration_seconds": requested_duration,
                "provider_payload_duration": provider_payload_duration_seconds(
                    self._settings.gptunnel_video_model
                ),
                "provider_reported_duration": provider_reported_duration_seconds(
                    self._settings.gptunnel_video_model
                ),
            }
            try:
                measured = probe_mp4_duration_seconds(file_path)
                duration_evidence["measured_mp4_duration"] = round(measured, 3)
                validation_status, delta = classify_duration_validation(
                    requested_seconds=requested_duration,
                    actual_seconds=measured,
                )
                duration_evidence["duration_delta_seconds"] = delta
                duration_evidence["difference_seconds"] = abs(delta)
                duration_evidence["difference_percent"] = round(
                    (abs(delta) / requested_duration) * 100, 2
                ) if requested_duration else None
                duration_evidence["duration_validation_status"] = validation_status.value
            except VideoDurationProbeError as exc:
                duration_evidence["duration_probe_error"] = exc.code
                validation_status = DurationValidationStatus.MISMATCH
                measured = None
                delta = None

            safe_meta = sanitize_generation_metadata(
                {
                    "clip_request_id": str(row.id),
                    "source_image_asset_id": str(row.source_image_asset_id),
                    "duration_seconds": row.duration_seconds,
                    "aspect_ratio": row.aspect_ratio,
                    "duration_validation": duration_evidence,
                    "execution_evidence": {
                        "estimated_cost_units": row.estimated_cost_units,
                        "latency_ms": evidence.get("latency_ms"),
                        "provider_job_id": row.provider_job_id,
                    },
                }
            )
            video_asset = GeneratedVisualAssetTable(
                id=asset_id,
                owner_id=owner_id,
                user_request_id=row.user_request_id or source.user_request_id,
                skill_code=SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value,
                skill_version="1.0",
                knowledge_snapshot_id=source.knowledge_snapshot_id,
                provider=provider_code,
                model=self._settings.gptunnel_video_model,
                generation_mode=GeneratedVisualGenerationMode.REAL,
                asset_type=GeneratedVisualAssetType.VIDEO_CLIP,
                prompt_summary=row.motion_brief[:1000],
                aspect_ratio=row.aspect_ratio,
                mime_type=downloaded.mime,
                storage_uri=f"/generated-visual-assets/{asset_id}/content",
                content_path=str(file_path.as_posix()),
                checksum=downloaded.checksum_sha256,
                status=GeneratedVisualAssetStatus.SUCCEEDED,
                safety_result="passed",
                generation_metadata=safe_meta,
                parent_asset_id=row.source_image_asset_id,
                created_at=utc_now(),
            )
            self._session.add(video_asset)

            prior_graph = row.scene_graph_json or {}
            scenes = copy.deepcopy(prior_graph.get("scenes") or [])
            if scenes and isinstance(scenes[0], dict):
                scenes[0] = {
                    **scenes[0],
                    "has_clip": True,
                    "clip_asset_id": str(asset_id),
                }
            row.scene_graph_json = {**copy.deepcopy(prior_graph), "scenes": scenes}
            flag_modified(row, "scene_graph_json")
            row.result_asset_id = asset_id
            if validation_status == DurationValidationStatus.MISMATCH:
                row.status = VideoClipRequestStatus.RESULT_REQUIRES_REVIEW
                row.error_code = "duration_contract_mismatch"
                row.error_message_ru = _OWNER_MESSAGE_DURATION_MISMATCH
            else:
                row.status = VideoClipRequestStatus.SUCCEEDED
                row.error_code = None
                row.error_message_ru = None
            row.execution_evidence_json = {
                **evidence,
                **duration_evidence,
                "checksum_sha256": downloaded.checksum_sha256,
                "result_mime": downloaded.mime,
                "result_size_bytes": downloaded.size_bytes,
                "completed_at": datetime.now(UTC).isoformat(),
            }
            row.updated_at = utc_now()
            await self._session.commit()
            await self._session.refresh(row)
            if row.status == VideoClipRequestStatus.SUCCEEDED and not image_to_video_live_verified(
                self._settings
            ):
                write_smoke_success(
                    provider_code=provider_code,
                    model=self._settings.gptunnel_video_model,
                    cost_units=row.estimated_cost_units,
                    checksum_sha256=downloaded.checksum_sha256,
                    result_asset_hint=str(asset_id),
                )
            return self._to_execution_public(row)
        except VideoDownloadError as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            evidence["download_error"] = exc.code
            if exc.code in _OUTCOME_UNKNOWN_DOWNLOAD_CODES:
                await self._mark_outcome_unknown(row, error_code=exc.code, evidence=evidence)
            else:
                await self._mark_failed(
                    row,
                    error_code=exc.code,
                    owner_message=_owner_message_for_error_code(exc.code),
                    evidence=evidence,
                )
            return self._to_execution_public(row)
        except Exception as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            evidence["persist_error"] = type(exc).__name__
            await self._mark_outcome_unknown(
                row,
                error_code="asset_persist_failed",
                evidence=evidence,
            )
            return self._to_execution_public(row)

    async def _mark_failed(
        self,
        row: VideoClipRequestTable,
        *,
        error_code: str,
        owner_message: str,
        evidence: dict[str, Any],
    ) -> None:
        row.status = VideoClipRequestStatus.FAILED
        row.error_code = error_code
        row.error_message_ru = owner_message
        row.execution_evidence_json = evidence
        row.updated_at = utc_now()
        await self._session.commit()

    async def _mark_outcome_unknown(
        self,
        row: VideoClipRequestTable,
        *,
        error_code: str,
        evidence: dict[str, Any],
    ) -> None:
        row.status = VideoClipRequestStatus.OUTCOME_UNKNOWN
        row.error_code = error_code
        row.error_message_ru = _OWNER_MESSAGE_OUTCOME_UNKNOWN
        row.execution_evidence_json = evidence
        row.updated_at = utc_now()
        await self._session.commit()

    def _to_execution_public(self, row: VideoClipRequestTable) -> VideoClipExecutionPublic:
        playback = (
            f"/generated-visual-assets/{row.result_asset_id}/content"
            if row.result_asset_id
            else None
        )
        evidence = row.execution_evidence_json or {}
        requested_duration = evidence.get("requested_duration_seconds", row.duration_seconds)
        actual_duration = evidence.get("measured_mp4_duration")
        delta = evidence.get("duration_delta_seconds")
        validation_raw = evidence.get("duration_validation_status")
        validation_status = (
            DurationValidationStatus(validation_raw)
            if validation_raw in DurationValidationStatus._value2member_map_
            else None
        )
        if row.status == VideoClipRequestStatus.SUCCEEDED:
            msg = "Клип готов. Проверьте результат и примите или создайте другой вариант."
        elif row.status == VideoClipRequestStatus.RESULT_REQUIRES_REVIEW:
            msg = row.error_message_ru or _OWNER_MESSAGE_DURATION_MISMATCH
        elif row.status == VideoClipRequestStatus.EXECUTING:
            msg = "Создаём клип…"
        elif row.status == VideoClipRequestStatus.OUTCOME_UNKNOWN:
            msg = row.error_message_ru or _OWNER_MESSAGE_OUTCOME_UNKNOWN
        elif row.status == VideoClipRequestStatus.FAILED:
            msg = row.error_message_ru or _owner_message_for_error_code(row.error_code)
        else:
            msg = "Ожидает подтверждения."
        return VideoClipExecutionPublic(
            clip_request_id=row.id,
            status=row.status,
            user_message_ru=msg,
            result_asset_id=row.result_asset_id,
            result_playback_uri=playback,
            requested_duration_seconds=int(requested_duration)
            if requested_duration is not None
            else row.duration_seconds,
            actual_duration_seconds=float(actual_duration)
            if actual_duration is not None
            else None,
            duration_delta_seconds=float(delta) if delta is not None else None,
            duration_validation_status=validation_status,
            can_accept=row.status == VideoClipRequestStatus.SUCCEEDED,
            can_retry_motion=row.status
            in {VideoClipRequestStatus.FAILED, VideoClipRequestStatus.RESULT_REQUIRES_REVIEW},
            can_create_variant=row.status == VideoClipRequestStatus.SUCCEEDED,
            can_add_to_project=row.status
            in {VideoClipRequestStatus.SUCCEEDED, VideoClipRequestStatus.RESULT_REQUIRES_REVIEW},
            can_reconcile=row.status
            in {VideoClipRequestStatus.OUTCOME_UNKNOWN, VideoClipRequestStatus.EXECUTING}
            and bool(row.provider_job_id),
            can_contact_admin=row.status == VideoClipRequestStatus.OUTCOME_UNKNOWN,
        )

    def _to_preview_public_from_row(self, row: VideoClipRequestTable) -> VideoClipPreviewPublic:
        ready = self._router.any_connected and image_to_video_live_verified(self._settings)
        blocked: str | None = None
        if not self._router.any_connected:
            blocked = "Генерация видео пока недоступна. Видеодвижок ещё не подключён."
        elif not image_to_video_live_verified(self._settings):
            blocked = (
                "Генерация видео пока недоступна. "
                "Функция будет активирована после проверки видеодвижка."
            )
        limitations = [
            "Движение зависит от описания и возможностей видеодвижка.",
            "Итог нужно визуально принять перед использованием в рекламе.",
        ]
        provider_durations = provider_reported_duration_seconds(
            self._settings.gptunnel_video_model
        )
        if provider_durations is not None and provider_durations != row.duration_seconds:
            limitations.append(
                f"Текущий видеодвижок создаёт клипы длительностью {provider_durations} с."
            )
        return VideoClipPreviewPublic(
            clip_request_id=row.id,
            status=row.status,
            motion_brief=row.motion_brief,
            duration_seconds=row.duration_seconds,
            aspect_ratio=row.aspect_ratio,
            estimated_cost_label=_cost_label(row.estimated_cost_units),
            estimated_wait_seconds=90,
            what_will_be_created_ru=(
                f"Короткий клип {row.duration_seconds} с ({row.aspect_ratio}) "
                "на основе вашего изображения."
            ),
            limitations_ru=limitations,
            ready_to_generate=ready,
            blocked_reason_ru=blocked,
        )

    async def get_by_source_image(
        self,
        *,
        owner_id: UUID,
        source_image_asset_id: UUID,
    ) -> VideoClipHydrationPublic | None:
        stmt = (
            select(VideoClipRequestTable)
            .where(
                VideoClipRequestTable.owner_id == owner_id,
                VideoClipRequestTable.source_image_asset_id == source_image_asset_id,
            )
            .order_by(VideoClipRequestTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        preview = (
            self._to_preview_public_from_row(row)
            if row.status == VideoClipRequestStatus.PREVIEW
            else None
        )
        execution = (
            self._to_execution_public(row)
            if row.status != VideoClipRequestStatus.PREVIEW
            else None
        )
        return VideoClipHydrationPublic(
            clip_request_id=row.id,
            status=row.status,
            source_image_asset_id=row.source_image_asset_id,
            preview=preview,
            execution=execution,
        )

    async def get_owner_acceptance_preview(self) -> VideoOwnerAcceptancePreviewPublic:
        row = await self._session.get(VideoClipRequestTable, CANONICAL_CLIP_REQUEST_ID)
        if row is None:
            raise InvalidStateError("clip_request_not_found")
        source = await self._session.get(
            GeneratedVisualAssetTable, CANONICAL_SOURCE_IMAGE_ASSET_ID
        )
        if source is None:
            raise InvalidStateError("source_asset_not_found")
        video = await self._session.get(GeneratedVisualAssetTable, CANONICAL_RESULT_ASSET_ID)
        brief = source.prompt_summary or row.motion_brief[:500]
        return VideoOwnerAcceptancePreviewPublic(
            source_image_asset_id=CANONICAL_SOURCE_IMAGE_ASSET_ID,
            clip_request_id=CANONICAL_CLIP_REQUEST_ID,
            result_asset_id=row.result_asset_id or CANONICAL_RESULT_ASSET_ID,
            user_request_id=row.user_request_id or source.user_request_id,
            seed_brief=brief,
            source_user_accepted=source.user_accepted is True,
            video_user_accepted=video.user_accepted if video is not None else None,
            execution=self._to_execution_public(row),
        )
