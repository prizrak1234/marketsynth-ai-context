"""Execute design.image_generation for UserRequest (Phase H2.6A cutover).

Mock = diagnostic only. Real user results require openai_images.
No publication, campaigns, budgets, or AgentRun.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.user_request import UserRequestTable
from app.domain.identity_preservation import (
    MSG_IDENTITY_MODE_UNSUPPORTED,
    MSG_QUALITY_GATE_REJECTED,
    assess_visual_consistency_assist,
    build_identity_profile,
    build_identity_prompt_sections,
    build_separated_provider_inputs,
    consistency_user_message,
)
from app.domain.image_prompt_integrity import (
    compute_generation_fingerprint,
    expected_subject_category,
    gross_semantic_mismatch,
    is_meta_only_image_prompt,
    prompt_hash,
    safe_prompt_debug,
)
from app.media_generation.contracts import ImageGenerationInput, MediaGenerationProvider
from app.media_generation.identity_provider import (
    IdentityProviderInput,
    OpenAIIdentityAdapter,
    UnsupportedIdentityAdapter,
)
from app.media_generation.openai_images_provider import OpenAIImagesProvider
from app.media_generation.provider_registry import get_image_provider
from app.media_generation.safe_metadata import sanitize_generation_metadata
from app.schemas.contracts import (
    GeneratedVisualAssetStatus,
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    SpecialistSkillCode,
    UserRequestStatus,
    VisualConsistencyLevel,
    VisualExecutionMode,
)

log = logging.getLogger(__name__)

_ASPECT_SIZES: dict[str, tuple[int, int, str]] = {
    "1:1": (1024, 1024, "1024x1024"),
    "16:9": (1792, 1024, "1792x1024"),
    "9:16": (1024, 1792, "1024x1792"),
    "4:5": (1024, 1280, "1024x1024"),
}

_MIN_BYTES = 100
_MAX_BYTES = 25 * 1024 * 1024
_MOCK_MARKER = "marketsynth_diagnostic_placeholder_v1"

MSG_DISABLED = "Генерация изображений сейчас отключена. Запрос сохранён, но изображение не создано."
MSG_NOT_CONFIGURED = (
    "Реальный генератор изображений пока не настроен. "
    "Запрос сохранён, но изображение не создано."
)
MSG_MOCK = (
    "Тестовый контур генерации работает. Это служебное изображение, "
    "а не результат AI-генерации."
)
MSG_PROGRESS = "Создаю изображение по вашему описанию…"
MSG_REAL_SUCCESS = 'Готово. Изображение создано и сохранено в разделе «Активы».'
MSG_REAL_SUCCESS_WITH_REFS = (
    "Изображение создано. Проверьте сходство с референсами. "
    "Marketsynth стремится максимально сохранить узнаваемые черты, но генеративная "
    "модель может внести изменения — сходство не гарантируется на 100%."
)
MSG_LOW_IDENTITY = MSG_QUALITY_GATE_REJECTED
MSG_SEMANTIC_MISMATCH = (
    "Результат не соответствует описанию и не принят системой. "
    "Можно повторить генерацию."
)
MSG_PROMPT_BINDING = (
    "Не хватает описания сцены: укажите, кого/что изобразить "
    "(не только «по промпту» / «по референсу»). Запрос сохранён."
)
MSG_REFERENCE_BINDING = (
    "Не удалось применить референсы. Генерация без них не выполнялась."
)
MSG_MOCK_FORBIDDEN = (
    "В этом окружении mock-результаты запрещены. "
    "Настройте реальный провайдер изображений."
)

_CATEGORY_MESSAGES = {
    "provider_disabled": MSG_DISABLED,
    "provider_misconfigured": MSG_NOT_CONFIGURED,
    "provider_unavailable": "Генератор изображений временно недоступен. Можно повторить позже.",
    "rate_limited": "Превышен лимит генерации. Подождите и повторите по явной команде.",
    "policy_rejected": "Запрос отклонён политикой безопасности провайдера.",
    "config_error": "Ошибка конфигурации генератора. Запрос сохранён.",
    "provider_empty_result": "Провайдер не вернул изображение. Запрос сохранён — можно повторить.",
    "invalid_payload": "Получен некорректный файл изображения. Запрос сохранён.",
    "mock_forbidden": MSG_MOCK_FORBIDDEN,
    "prompt_binding_failure": MSG_PROMPT_BINDING,
    "reference_binding_failure": MSG_REFERENCE_BINDING,
    "identity_mode_not_supported": MSG_IDENTITY_MODE_UNSUPPORTED,
    "semantic_mismatch": MSG_SEMANTIC_MISMATCH,
    "stale_asset_reuse": "Найден устаревший результат по другому запросу — повторная выдача заблокирована.",
    "unknown": "Не удалось создать изображение. Запрос сохранён — можно повторить.",
}


def _prompt_summary(text: str, limit: int = 240) -> str:
    cleaned = " ".join((text or "").strip().split())
    return cleaned[:limit]


def _resolve_aspect(inputs: dict) -> tuple[str, int, int, str]:
    aspect = str(inputs.get("aspect_ratio") or "1:1").strip()
    if aspect not in _ASPECT_SIZES:
        aspect = "1:1"
    w, h, size = _ASPECT_SIZES[aspect]
    return aspect, w, h, size


def _has_openai_key(settings: Settings) -> bool:
    key = settings.openai_api_key
    return bool(key and key.get_secret_value().strip())


def _has_gptunnel_key(settings: Settings) -> bool:
    key = settings.gptunnel_api_key
    return bool(key and key.get_secret_value().strip())


def _write_mock_png(path: Path, *, prompt: str, width: int, height: int) -> str:
    """Diagnostic placeholder PNG — never a user-facing AI result."""
    from PIL import Image, ImageDraw, ImageFont

    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(prompt.encode("utf-8")).digest()
    bg = (40 + digest[0] % 80, 50 + digest[1] % 90, 70 + digest[2] % 100)
    accent = (180 + digest[3] % 60, 120 + digest[4] % 80, 90 + digest[5] % 100)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, width - 40, height // 3], fill=accent)
    draw.ellipse(
        [width // 4, height // 3, width * 3 // 4, height * 5 // 6],
        fill=(min(255, bg[0] + 40), min(255, bg[1] + 30), min(255, bg[2] + 20)),
    )
    try:
        font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None
    draw.multiline_text(
        (56, 56),
        f"TEST PLACEHOLDER\n{_MOCK_MARKER}\n{_prompt_summary(prompt, 60)}",
        fill=(255, 255, 255),
        font=font,
        spacing=6,
    )
    img.save(path, format="PNG")
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


async def _download_to_file(url: str, path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return resp.content


def _validate_image_bytes(payload: bytes, *, path: Path) -> tuple[str, int, int]:
    if len(payload) < _MIN_BYTES or len(payload) > _MAX_BYTES:
        raise ImageGenerationUnavailableError("invalid_payload", _CATEGORY_MESSAGES["invalid_payload"])
    if payload[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif payload[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ImageGenerationUnavailableError("invalid_payload", _CATEGORY_MESSAGES["invalid_payload"])
    # Reject known diagnostic marker text in PNG if somehow labeled
    if _MOCK_MARKER.encode("utf-8") in payload:
        raise ImageGenerationUnavailableError("invalid_payload", _CATEGORY_MESSAGES["invalid_payload"])
    width = height = 0
    try:
        from PIL import Image

        with Image.open(path) as img:
            width, height = img.size
    except Exception as exc:  # noqa: BLE001
        log.warning("image_dimension_read_failed", extra={"error": type(exc).__name__})
    if width <= 0 or height <= 0:
        raise ImageGenerationUnavailableError("invalid_payload", _CATEGORY_MESSAGES["invalid_payload"])
    return mime, width, height


def _map_provider_error(exc: Exception) -> ImageGenerationUnavailableError:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "rate" in text or "429" in text:
        return ImageGenerationUnavailableError("rate_limited", _CATEGORY_MESSAGES["rate_limited"])
    if "policy" in text or "safety" in text or ("content" in text and "filter" in text):
        return ImageGenerationUnavailableError("policy_rejected", _CATEGORY_MESSAGES["policy_rejected"])
    if (
        "auth" in name
        or "auth" in text
        or "api key" in text
        or "incorrect api key" in text
        or "401" in text
        or "403" in text
    ):
        return ImageGenerationUnavailableError("config_error", MSG_NOT_CONFIGURED)
    if "timeout" in text or "unavailable" in text or "503" in text or "502" in text:
        return ImageGenerationUnavailableError(
            "provider_unavailable", _CATEGORY_MESSAGES["provider_unavailable"]
        )
    if isinstance(exc, InvalidStateError):
        return ImageGenerationUnavailableError("config_error", _CATEGORY_MESSAGES["config_error"])
    log.warning("image_provider_failed", extra={"error": type(exc).__name__})
    return ImageGenerationUnavailableError("unknown", _CATEGORY_MESSAGES["unknown"])


class ImageGenerationUnavailableError(RuntimeError):
    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.user_message = message


class DesignImageGenerationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    def readiness(self) -> dict:
        enabled = bool(self._settings.image_generation_enabled)
        provider = (self._settings.image_generation_provider or "mock").strip().lower()
        if provider not in {"mock", "openai_images", "gptunnel"}:
            provider = "mock"
        app_env = (self._settings.app_env or "development").strip().lower()
        allow_mock = bool(self._settings.allow_mock_image_results)
        if app_env in {"production", "prod"}:
            allow_mock = False
        openai_key_present = _has_openai_key(self._settings)
        gptunnel_key_present = _has_gptunnel_key(self._settings)
        openai_media_gate = bool(
            self._settings.media_generation_enabled and self._settings.openai_images_enabled
        )
        fallback = (self._settings.image_generation_fallback_provider or "").strip().lower()
        provider_ready = (provider == "mock" and allow_mock and enabled) or (
            provider == "openai_images" and enabled and openai_key_present
        ) or (provider == "gptunnel" and enabled and gptunnel_key_present)
        mock_only = provider == "mock"
        real_generation_available = enabled and (
            (provider == "openai_images" and openai_key_present)
            or (provider == "gptunnel" and gptunnel_key_present)
            or (fallback == "gptunnel" and gptunnel_key_present and openai_key_present)
        )
        can_generate_user_result = bool(
            enabled
            and (
                (provider == "openai_images" and openai_key_present)
                or (provider == "gptunnel" and gptunnel_key_present)
            )
        )
        can_generate_diagnostic = enabled and mock_only and allow_mock
        return {
            "image_generation_enabled": enabled,
            "configured_provider": provider,
            "fallback_provider": fallback or None,
            "provider_ready": bool(provider_ready),
            "real_generation_available": bool(real_generation_available),
            "mock_only": bool(mock_only),
            "allow_mock_image_results": allow_mock,
            "can_generate_user_result": bool(can_generate_user_result),
            "can_generate_diagnostic": bool(can_generate_diagnostic),
            "can_generate": bool(can_generate_user_result or can_generate_diagnostic),
            "openai_images_configured": bool(openai_key_present and (openai_media_gate or enabled)),
            "gptunnel_configured": bool(gptunnel_key_present and enabled),
        }

    def _resolve_openai_provider(self) -> OpenAIImagesProvider:
        return OpenAIImagesProvider(self._settings, allow_h26a_gate=True)

    def _resolve_gptunnel_provider(self):
        from app.media_generation.gptunnel_images_provider import GptunnelImagesProvider

        return GptunnelImagesProvider(self._settings)

    async def execute_for_user_request(
        self,
        row: UserRequestTable,
        *,
        prompt: str,
        skill_inputs: dict | None = None,
    ) -> GeneratedVisualAssetTable:
        ready = self.readiness()
        if not ready["image_generation_enabled"]:
            raise ImageGenerationUnavailableError("provider_disabled", MSG_DISABLED)

        inputs = dict(skill_inputs or row.skill_inputs or {})
        effective_prompt = str(prompt or inputs.get("prompt") or row.text or "").strip()
        # Carry a prior substantive prompt when the user only says "по промпту + референс".
        if is_meta_only_image_prompt(effective_prompt):
            prior = str(inputs.get("_prior_prompt") or "").strip()
            if prior and not is_meta_only_image_prompt(prior):
                effective_prompt = prior
                inputs["prompt"] = prior
                inputs["_prompt_recovered_from_prior"] = "1"
            else:
                raise ImageGenerationUnavailableError(
                    "prompt_binding_failure", MSG_PROMPT_BINDING
                )

        aspect, width, height, size = _resolve_aspect(inputs)
        n = 1
        provider_name = (self._settings.image_generation_provider or "mock").strip().lower()
        if provider_name not in {"mock", "openai_images", "gptunnel"}:
            provider_name = "mock"

        if provider_name == "mock":
            if not ready["allow_mock_image_results"]:
                raise ImageGenerationUnavailableError("mock_forbidden", MSG_MOCK_FORBIDDEN)
            return await self._execute_mock(
                row,
                prompt=effective_prompt,
                aspect=aspect,
                width=width,
                height=height,
                size=size,
            )

        if provider_name == "gptunnel":
            if not _has_gptunnel_key(self._settings):
                raise ImageGenerationUnavailableError("provider_misconfigured", MSG_NOT_CONFIGURED)
            return await self._execute_openai(
                row,
                prompt=effective_prompt,
                aspect=aspect,
                width=width,
                height=height,
                size=size,
                n=n,
                skill_inputs=inputs,
                provider_name="gptunnel",
            )

        fallback = (self._settings.image_generation_fallback_provider or "").strip().lower()
        openai_ok = _has_openai_key(self._settings)
        gptunnel_ok = _has_gptunnel_key(self._settings)

        if not openai_ok:
            if fallback == "gptunnel" and gptunnel_ok:
                log.warning("image_provider_fallback_gptunnel", extra={"reason": "openai_key_missing"})
                return await self._execute_openai(
                    row,
                    prompt=effective_prompt,
                    aspect=aspect,
                    width=width,
                    height=height,
                    size=size,
                    n=n,
                    skill_inputs=inputs,
                    provider_name="gptunnel",
                )
            raise ImageGenerationUnavailableError("provider_misconfigured", MSG_NOT_CONFIGURED)

        try:
            return await self._execute_openai(
                row,
                prompt=effective_prompt,
                aspect=aspect,
                width=width,
                height=height,
                size=size,
                n=n,
                skill_inputs=inputs,
                provider_name="openai_images",
            )
        except ImageGenerationUnavailableError as exc:
            if (
                fallback == "gptunnel"
                and gptunnel_ok
                and exc.category
                not in {
                    "prompt_binding_failure",
                    "reference_binding_failure",
                    "semantic_mismatch",
                    "policy_rejected",
                }
            ):
                log.warning(
                    "image_provider_fallback_gptunnel",
                    extra={"from_category": exc.category},
                )
                return await self._execute_openai(
                    row,
                    prompt=effective_prompt,
                    aspect=aspect,
                    width=width,
                    height=height,
                    size=size,
                    n=n,
                    skill_inputs=inputs,
                    provider_name="gptunnel",
                )
            raise
        except InvalidStateError as exc:
            if fallback == "gptunnel" and gptunnel_ok and not inputs.get("reference_set_id"):
                log.warning(
                    "image_provider_fallback_gptunnel",
                    extra={"from": type(exc).__name__},
                )
                return await self._execute_openai(
                    row,
                    prompt=effective_prompt,
                    aspect=aspect,
                    width=width,
                    height=height,
                    size=size,
                    n=n,
                    skill_inputs=inputs,
                    provider_name="gptunnel",
                )
            raise ImageGenerationUnavailableError("provider_misconfigured", MSG_NOT_CONFIGURED) from exc

    async def _execute_mock(
        self,
        row: UserRequestTable,
        *,
        prompt: str,
        aspect: str,
        width: int,
        height: int,
        size: str,
    ) -> GeneratedVisualAssetTable:
        provider = get_image_provider(MediaGenerationProvider.MOCK, self._settings)
        gen_input = ImageGenerationInput(prompt=prompt[:4000], size=size, n=1)
        result = await provider.generate_image(gen_input)  # type: ignore[union-attr]
        asset_id = uuid4()
        file_path = Path(self._settings.image_generation_storage_dir) / f"{asset_id}.png"
        checksum = _write_mock_png(file_path, prompt=prompt, width=width, height=height)
        safe_meta = sanitize_generation_metadata(
            {
                **(result.safe_metadata or {}),
                "aspect_ratio": aspect,
                "skill_code": SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value,
                "user_request_id": str(row.id),
                "generation_mode": GeneratedVisualGenerationMode.MOCK.value,
                "asset_type": GeneratedVisualAssetType.DIAGNOSTIC_PLACEHOLDER.value,
                "diagnostic_marker": _MOCK_MARKER,
                "is_user_result": False,
                "warnings": ["mock_diagnostic_placeholder"],
            }
        )
        asset = GeneratedVisualAssetTable(
            id=asset_id,
            owner_id=row.owner_id,
            user_request_id=row.id,
            skill_code=SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value,
            skill_version=row.skill_version or "1.0",
            knowledge_snapshot_id=row.knowledge_snapshot_id,
            provider="mock",
            model=None,
            generation_mode=GeneratedVisualGenerationMode.MOCK,
            asset_type=GeneratedVisualAssetType.DIAGNOSTIC_PLACEHOLDER,
            prompt_summary=_prompt_summary(prompt),
            aspect_ratio=aspect,
            width=width,
            height=height,
            mime_type="image/png",
            storage_uri=f"/generated-visual-assets/{asset_id}/content",
            content_path=str(file_path.as_posix()),
            checksum=checksum,
            status=GeneratedVisualAssetStatus.DIAGNOSTIC,
            safety_result="diagnostic",
            generation_metadata=safe_meta,
            error_category=None,
            created_at=utc_now(),
        )
        self._session.add(asset)
        await self._session.commit()
        await self._session.refresh(asset)
        return asset

    async def _execute_openai(
        self,
        row: UserRequestTable,
        *,
        prompt: str,
        aspect: str,
        width: int,
        height: int,
        size: str,
        n: int,
        skill_inputs: dict | None = None,
        provider_name: str = "openai_images",
    ) -> GeneratedVisualAssetTable:
        if provider_name == "gptunnel":
            provider = self._resolve_gptunnel_provider()
            model = self._settings.gptunnel_images_model
        else:
            provider = self._resolve_openai_provider()
            model = self._settings.openai_images_model
        gen_input = ImageGenerationInput(prompt=prompt[:4000], size=size, n=n)
        inputs = dict(skill_inputs or {})
        reference_set_id = inputs.get("reference_set_id")
        used_refs: list = []
        excluded_refs: list = []
        selection_summary = ""
        generation_mode_label = VisualExecutionMode.TEXT_TO_IMAGE.value
        last_error: Exception | None = None
        result = None
        identity_lineage = None
        selection_payload = None

        strengthen_mode = str(inputs.get("strengthen_likeness") or "").lower() in {
            "1",
            "true",
            "yes",
        } or str(inputs.get("identity_fidelity") or "").lower() == "maximum"
        parent_asset_id_raw = (inputs.get("parent_asset_id") or "").strip() or None
        # Prefer explicit skill_input trait lists when provided (H2.8C composer).
        skill_preserve = [
            p.strip()
            for p in str(inputs.get("preserve_traits") or "").split(",")
            if p.strip()
        ]
        skill_allowed = [
            p.strip()
            for p in str(inputs.get("allowed_changes") or "").split(",")
            if p.strip()
        ]
        identity_profile = None
        identity_prompt = prompt
        primary_ref_id = None
        refs_in_set = 0
        require_identity_mode = bool(reference_set_id) or str(
            inputs.get("execution_mode") or ""
        ).strip() == VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value

        if reference_set_id and provider_name == "openai_images":
            from uuid import UUID as _UUID

            from app.db.models.reference_visual import (
                ReferenceSetTable,
                ReferenceVisualAssetTable,
            )
            from app.reference_images.service import ReferenceImageService, ReferenceUploadError

            try:
                selection = await ReferenceImageService(
                    self._session, self._settings
                ).select_for_provider(
                    owner_id=row.owner_id,
                    set_id=_UUID(str(reference_set_id)),
                )
            except ReferenceUploadError as exc:
                raise ImageGenerationUnavailableError(
                    "reference_binding_failure", exc.message
                ) from exc
            selection_payload = selection
            used_refs = list(selection.selected_reference_ids)
            excluded_refs = list(selection.excluded_reference_ids)
            selection_summary = selection.selection_summary
            ref_set = await self._session.get(ReferenceSetTable, _UUID(str(reference_set_id)))
            refs_in_set = len(ref_set.reference_asset_ids or []) if ref_set else len(used_refs)
            # Honor composer primary when present in set.
            composer_primary = (inputs.get("primary_reference_id") or "").strip()
            if composer_primary:
                try:
                    composer_uuid = _UUID(composer_primary)
                    if composer_uuid in used_refs or (
                        ref_set and composer_uuid in (ref_set.reference_asset_ids or [])
                    ):
                        primary_ref_id = composer_uuid
                        if ref_set and ref_set.primary_reference_id != composer_uuid:
                            ref_set.primary_reference_id = composer_uuid
                            self._session.add(ref_set)
                except ValueError:
                    pass
            if primary_ref_id is None:
                primary_ref_id = (
                    selection.primary_reference_id
                    or (
                        ref_set.primary_reference_id
                        if ref_set and ref_set.primary_reference_id in used_refs
                        else (used_refs[0] if used_refs else None)
                    )
                )
            identity_profile = build_identity_profile(
                primary_reference_id=primary_ref_id,
                reference_asset_ids=used_refs,
                immutable_traits=skill_preserve
                or (list(ref_set.immutable_traits or []) if ref_set else None),
                allowed_variations=skill_allowed
                or (list(ref_set.allowed_variations or []) if ref_set else None),
                forbidden_changes=list(ref_set.forbidden_changes or []) if ref_set else None,
                user_notes=ref_set.identity_notes if ref_set else None,
                strengthen_mode=strengthen_mode,
            )
            sections = build_separated_provider_inputs(
                scene_prompt=prompt,
                profile=identity_profile,
            )
            identity_prompt = build_identity_prompt_sections(
                scene_prompt=prompt,
                profile=identity_profile,
            )
            primary = primary_ref_id or (used_refs[0] if used_refs else None)
            if primary is None:
                raise ImageGenerationUnavailableError(
                    "reference_binding_failure", MSG_REFERENCE_BINDING
                )
            pref = await self._session.get(ReferenceVisualAssetTable, primary)
            if not pref or not pref.content_path:
                raise ImageGenerationUnavailableError(
                    "reference_binding_failure", MSG_REFERENCE_BINDING
                )
            adapter = OpenAIIdentityAdapter(provider, model=model)
            try:
                id_input = IdentityProviderInput(
                    identity_section=sections["identity"],
                    scene_section=sections["scene"],
                    style_section=sections["style"],
                    negative_section=sections["negative"],
                    primary_image_path=pref.content_path,
                    supporting_image_paths=[],
                    primary_reference_id=primary,
                    transmitted_reference_ids=[primary],
                    identity_fidelity=str(inputs.get("identity_fidelity") or "maximum"),
                    style_freedom=str(inputs.get("style_freedom") or "low"),
                    size=size if size in {"256x256", "512x512", "1024x1024"} else "1024x1024",
                    execution_mode=VisualExecutionMode.PERSON_IDENTITY_PRESERVATION,
                    roles=[
                        {
                            "reference_id": str(r.reference_id),
                            "purpose": r.purpose,
                            "group": r.group.value if hasattr(r.group, "value") else str(r.group),
                            "role_label": r.role_label,
                            "is_primary": r.is_primary,
                            "selected": r.selected,
                            "exclusion_reason": r.exclusion_reason,
                        }
                        for r in (selection_payload.roles or [])
                    ]
                    if selection_payload is not None
                    else [],
                )
                result, identity_lineage = await adapter.generate_with_identity(id_input)
                generation_mode_label = VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value
            except Exception as exc:  # noqa: BLE001
                if str(exc) == "identity_mode_not_supported":
                    raise ImageGenerationUnavailableError(
                        "identity_mode_not_supported", MSG_IDENTITY_MODE_UNSUPPORTED
                    ) from exc
                log.warning(
                    "reference_edit_failed_no_silent_fallback",
                    extra={"error": type(exc).__name__},
                )
                mapped = _map_provider_error(exc)
                if mapped.category in {"policy_rejected", "rate_limited", "config_error"}:
                    raise mapped from exc
                raise ImageGenerationUnavailableError(
                    "reference_binding_failure", MSG_REFERENCE_BINDING
                ) from exc
        elif reference_set_id and provider_name == "gptunnel":
            # H2.8D: GPTunnel cannot person_identity_preservation — fail closed.
            _ = UnsupportedIdentityAdapter("gptunnel")
            raise ImageGenerationUnavailableError(
                "identity_mode_not_supported", MSG_IDENTITY_MODE_UNSUPPORTED
            )

        if result is None:
            if require_identity_mode:
                # Refs were requested; never silently fall back to text-only.
                raise ImageGenerationUnavailableError(
                    "reference_binding_failure", MSG_REFERENCE_BINDING
                )
            for attempt in range(2):  # initial + one controlled retry
                try:
                    result = await provider.generate_image(gen_input)
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    mapped = _map_provider_error(exc)
                    if mapped.category in {"rate_limited", "policy_rejected", "config_error"}:
                        raise mapped from exc
                    if attempt == 0:
                        log.warning(
                            "image_provider_retry",
                            extra={"error": type(exc).__name__, "attempt": attempt},
                        )
                        continue
                    raise mapped from exc
        if result is None:
            raise _map_provider_error(last_error or RuntimeError("empty"))

        asset_id = uuid4()
        storage_root = Path(self._settings.image_generation_storage_dir)
        ext = ".png"
        if result.mime_type == "image/webp":
            ext = ".webp"
        elif result.mime_type == "image/jpeg":
            ext = ".jpg"
        file_path = storage_root / f"{asset_id}{ext}"
        ref = result.provider_asset_ref
        payload: bytes | None = None
        if result.image_bytes:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(result.image_bytes)
            payload = result.image_bytes
        elif ref and str(ref).startswith("http"):
            try:
                payload = await _download_to_file(str(ref), file_path)
            except Exception as exc:  # noqa: BLE001
                raise _map_provider_error(exc) from exc
        else:
            raise ImageGenerationUnavailableError(
                "provider_empty_result", _CATEGORY_MESSAGES["provider_empty_result"]
            )

        mime, real_w, real_h = _validate_image_bytes(payload, path=file_path)
        checksum = "sha256:" + hashlib.sha256(payload).hexdigest()
        usage = {}
        if isinstance(result.safe_metadata, dict):
            for key in ("usage", "cost", "image_count", "size", "revision", "mode"):
                if key in result.safe_metadata:
                    usage[key] = result.safe_metadata[key]

        transmitted_count = (
            identity_lineage.transmitted_count
            if identity_lineage is not None
            else (1 if used_refs and generation_mode_label == VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value else 0)
        )
        consistency = assess_visual_consistency_assist(
            used_reference_count=len(used_refs),
            strengthen_mode=strengthen_mode,
            generation_mode=generation_mode_label,
            transmitted_count=transmitted_count,
        )
        provider_prompt = identity_prompt if used_refs else prompt
        debug = safe_prompt_debug(provider_prompt)
        transmitted_ids = (
            list(identity_lineage.transmitted_reference_ids)
            if identity_lineage is not None
            else ([str(primary_ref_id)] if primary_ref_id else [])
        )
        safe_meta = sanitize_generation_metadata(
            {
                **(result.safe_metadata or {}),
                **usage,
                "aspect_ratio": aspect,
                "skill_code": SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value,
                "user_request_id": str(row.id),
                "generation_mode": GeneratedVisualGenerationMode.REAL.value,
                "asset_type": GeneratedVisualAssetType.USER_RESULT.value,
                "is_user_result": True,
                "provider_model": model,
                "visual_generation_mode": generation_mode_label,
                "requested_generation_mode": (
                    VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value
                    if reference_set_id
                    else VisualExecutionMode.TEXT_TO_IMAGE.value
                ),
                "requested_mode": (
                    VisualExecutionMode.PERSON_IDENTITY_PRESERVATION.value
                    if reference_set_id
                    else VisualExecutionMode.TEXT_TO_IMAGE.value
                ),
                "actual_mode": generation_mode_label,
                "input_fidelity": "high" if used_refs else "n/a",
                "selection_summary": selection_summary[:500] if selection_summary else None,
                "prompt_hash": prompt_hash(provider_prompt),
                "identity_prompt_hash": prompt_hash(identity_prompt) if used_refs else None,
                "prompt_preview": debug.get("prompt_preview"),
                "prompt_length": debug.get("prompt_length"),
                "is_meta_only": debug.get("is_meta_only"),
                "expected_subject": expected_subject_category(prompt),
                "input_fingerprint": compute_generation_fingerprint(
                    prompt=provider_prompt,
                    user_request_id=str(row.id),
                    reference_set_id=str(reference_set_id) if reference_set_id else None,
                    selected_reference_ids=[str(x) for x in used_refs],
                    size=size,
                    style=str(inputs.get("style") or "default"),
                    preservation=(
                        "identity_strengthen"
                        if strengthen_mode and used_refs
                        else ("identity_maximize" if used_refs else "none")
                    ),
                    provider=provider_name,
                    model=str(model or ""),
                    generation_mode=generation_mode_label,
                ),
                # H2.8D honest transmit counts
                "references_selected_count": len(used_refs),
                "references_count_in_set": refs_in_set,
                "references_provider_received": transmitted_count,
                "transmitted_reference_ids": transmitted_ids,
                "primary_reference_id": str(primary_ref_id) if primary_ref_id else None,
                "primary_reference_position": (
                    identity_lineage.primary_position if identity_lineage else (0 if primary_ref_id else None)
                ),
                "selected_reference_ids": [str(x) for x in used_refs],
                "excluded_reference_ids": [str(x) for x in excluded_refs],
                "identity_selected_count": (
                    selection_payload.identity_selected_count if selection_payload else len(used_refs)
                ),
                "style_selected_count": (
                    selection_payload.style_selected_count if selection_payload else 0
                ),
                "identity_profile_version": (
                    identity_profile.version if identity_profile else None
                ),
                "identity_strengthen_mode": strengthen_mode,
                "visual_consistency": consistency.value,
                "parent_asset_id": parent_asset_id_raw,
                "prompt_section_hashes": (
                    identity_lineage.prompt_section_hashes if identity_lineage else None
                ),
                "transmitted_original_dimensions": (
                    identity_lineage.original_dimensions if identity_lineage else None
                ),
                "transmitted_dimensions": (
                    identity_lineage.transmitted_dimensions if identity_lineage else None
                ),
                "transmitted_checksums": (
                    identity_lineage.checksums if identity_lineage else None
                ),
                "transmitted_mime_types": (
                    identity_lineage.mime_types if identity_lineage else None
                ),
                "provider_request_id": (
                    identity_lineage.provider_request_id if identity_lineage else None
                ),
                "provider_capability": (
                    identity_lineage.capability.value if identity_lineage else None
                ),
                "selection_roles": (
                    [
                        {
                            "reference_id": str(r.reference_id),
                            "purpose": r.purpose,
                            "group": r.group.value if hasattr(r.group, "value") else str(r.group),
                            "role_label": r.role_label,
                            "is_primary": r.is_primary,
                            "selected": r.selected,
                            "exclusion_reason": r.exclusion_reason,
                        }
                        for r in (selection_payload.roles or [])
                    ]
                    if selection_payload is not None
                    else (
                        identity_lineage.roles
                        if identity_lineage is not None
                        else None
                    )
                ),
                "ab_variant": (inputs.get("ab_variant") or None),
                # H2.8E honesty: selected vs actually transmitted
                "selected_but_not_transmitted_ids": [
                    str(x)
                    for x in used_refs
                    if str(x) not in {str(i) for i in transmitted_ids}
                ],
                "selected_but_not_transmitted_reason": (
                    "provider_adapter_limit"
                    if used_refs and len(transmitted_ids) < len(used_refs)
                    else None
                ),
                "references_provider_received_count": transmitted_count,
                "safe_transmit_note_ru": (
                    "Текущий генератор использовал 1 основной референс. "
                    "Дополнительные ракурсы сохранены, но этим провайдером не передаются."
                    if used_refs and transmitted_count <= 1 and len(used_refs) > 1
                    else None
                ),
            }
        )
        for key in list(safe_meta.keys()):
            if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                safe_meta.pop(key, None)

        initial_status = (
            GeneratedVisualAssetStatus.AWAITING_IDENTITY_REVIEW
            if used_refs
            else GeneratedVisualAssetStatus.SUCCEEDED
        )
        # Quality gate: low similarity is not presented as success.
        if used_refs and consistency == VisualConsistencyLevel.LOW and not strengthen_mode:
            initial_status = GeneratedVisualAssetStatus.REJECTED_BY_QUALITY_GATE
        parent_uuid = None
        if parent_asset_id_raw:
            try:
                parent_uuid = UUID(str(parent_asset_id_raw))
            except ValueError:
                parent_uuid = None
        asset = GeneratedVisualAssetTable(
            id=asset_id,
            owner_id=row.owner_id,
            user_request_id=row.id,
            skill_code=SpecialistSkillCode.DESIGN_IMAGE_GENERATION.value,
            skill_version=row.skill_version or "1.0",
            knowledge_snapshot_id=row.knowledge_snapshot_id,
            provider=provider_name,
            model=model,
            generation_mode=GeneratedVisualGenerationMode.REAL,
            asset_type=(
                GeneratedVisualAssetType.IDENTITY_AB_CHILD
                if parent_uuid
                else GeneratedVisualAssetType.USER_RESULT
            ),
            prompt_summary=_prompt_summary(prompt),
            aspect_ratio=aspect,
            width=real_w or result.width or width,
            height=real_h or result.height or height,
            mime_type=mime,
            storage_uri=f"/generated-visual-assets/{asset_id}/content",
            content_path=str(file_path.as_posix()),
            checksum=checksum,
            status=initial_status,
            safety_result="passed",
            generation_metadata=safe_meta,
            error_category=(
                "rejected_by_quality_gate"
                if initial_status == GeneratedVisualAssetStatus.REJECTED_BY_QUALITY_GATE
                else None
            ),
            reference_set_id=UUID(str(reference_set_id)) if reference_set_id else None,
            used_reference_ids=[str(x) for x in used_refs],
            excluded_reference_ids=[str(x) for x in excluded_refs],
            identity_similarity=consistency.value if used_refs else "not_applicable",
            brand_similarity="not_applicable" if not used_refs else None,
            user_accepted=False
            if initial_status == GeneratedVisualAssetStatus.REJECTED_BY_QUALITY_GATE
            else None,
            review_notes=(
                "rejected_by_quality_gate"
                if initial_status == GeneratedVisualAssetStatus.REJECTED_BY_QUALITY_GATE
                else None
            ),
            parent_asset_id=parent_uuid,
            created_at=utc_now(),
        )
        self._session.add(asset)
        await self._session.commit()
        await self._session.refresh(asset)
        # Stash for success message selection
        asset.generation_metadata = {
            **(asset.generation_metadata or {}),
            "_used_refs": bool(used_refs),
            "visual_consistency": consistency.value,
        }
        return asset


def apply_generation_success(
    row: UserRequestTable,
    asset: GeneratedVisualAssetTable,
    *,
    warnings: list[str] | None = None,
) -> None:
    ids = [str(x) for x in (row.generated_visual_asset_ids or [])]
    ids.append(str(asset.id))
    row.generated_visual_asset_ids = ids
    mode = asset.generation_mode
    meta = dict(asset.generation_metadata or {})
    observed = meta.get("observed_subject_category")
    expected = meta.get("expected_subject") or expected_subject_category(
        asset.prompt_summary or ""
    )
    mismatch = bool(meta.get("semantic_mismatch")) or gross_semantic_mismatch(
        expected_category=str(expected),
        observed_category=str(observed) if observed else None,
    )
    if mode == GeneratedVisualGenerationMode.MOCK or asset.asset_type == (
        GeneratedVisualAssetType.DIAGNOSTIC_PLACEHOLDER
    ):
        row.generation_status = GeneratedVisualAssetStatus.DIAGNOSTIC.value
        row.assistant_message = MSG_MOCK[:4000]
        row.generation_warnings = list(
            warnings or ["mock_diagnostic_placeholder", "not_user_result"]
        )
        row.status = UserRequestStatus.COMPLETED
        row.next_action_label = "Диагностика"
        row.next_href = "/workspace/assets"
    elif mismatch:
        row.generation_status = "semantic_mismatch"
        row.assistant_message = MSG_SEMANTIC_MISMATCH[:4000]
        row.generation_warnings = list(
            dict.fromkeys([*(warnings or []), "semantic_mismatch"])
        )
        row.status = UserRequestStatus.COMPLETED
        row.next_action_label = "Повторить генерацию"
        row.next_href = "/workspace/assets"
        asset.status = GeneratedVisualAssetStatus.SUCCEEDED
        asset.user_accepted = False
        asset.review_notes = "semantic_mismatch"
        meta["semantic_mismatch"] = True
        asset.generation_metadata = meta
    else:
        used_refs = bool(meta.get("_used_refs")) or bool(asset.used_reference_ids)
        consistency_raw = str(meta.get("visual_consistency") or "")
        try:
            consistency = VisualConsistencyLevel(consistency_raw)
        except ValueError:
            consistency = (
                VisualConsistencyLevel.LOW
                if used_refs and len(asset.used_reference_ids or []) < 3
                else VisualConsistencyLevel.UNAVAILABLE
            )
        if used_refs:
            assist_msg = consistency_user_message(consistency)
            if consistency == VisualConsistencyLevel.LOW and asset.status == (
                GeneratedVisualAssetStatus.REJECTED_BY_QUALITY_GATE
            ):
                row.generation_status = (
                    GeneratedVisualAssetStatus.REJECTED_BY_QUALITY_GATE.value
                )
                row.assistant_message = (assist_msg or MSG_LOW_IDENTITY)[:4000]
                row.generation_warnings = list(
                    dict.fromkeys(
                        [
                            *(warnings or []),
                            "low_identity_consistency",
                            "rejected_by_quality_gate",
                        ]
                    )
                )
                row.next_action_label = "Повторить с основным референсом"
            else:
                asset.status = GeneratedVisualAssetStatus.AWAITING_IDENTITY_REVIEW
                row.generation_status = (
                    GeneratedVisualAssetStatus.AWAITING_IDENTITY_REVIEW.value
                )
                if assist_msg or consistency == VisualConsistencyLevel.LOW:
                    row.assistant_message = (assist_msg or MSG_LOW_IDENTITY)[:4000]
                    row.generation_warnings = list(
                        dict.fromkeys(
                            [
                                *(warnings or []),
                                "low_identity_consistency",
                                "awaiting_identity_review",
                            ]
                        )
                    )
                else:
                    row.assistant_message = MSG_REAL_SUCCESS_WITH_REFS[:4000]
                    row.generation_warnings = list(
                        dict.fromkeys([*(warnings or []), "awaiting_identity_review"])
                    )
                row.next_action_label = "Проверить сходство"
        else:
            row.generation_status = GeneratedVisualAssetStatus.SUCCEEDED.value
            row.assistant_message = MSG_REAL_SUCCESS[:4000]
            row.generation_warnings = list(warnings or [])
            row.next_action_label = "Открыть в Активах"
        row.status = UserRequestStatus.COMPLETED
        row.next_href = "/workspace/assets"
    row.updated_at = utc_now()


def apply_generation_unavailable(
    row: UserRequestTable,
    *,
    message: str,
    category: str,
) -> None:
    row.generation_status = GeneratedVisualAssetStatus.UNAVAILABLE.value
    row.generation_warnings = [category]
    row.assistant_message = message[:4000]
    row.next_action_label = "Повторить позже"
    row.updated_at = utc_now()


def apply_generation_progress(row: UserRequestTable) -> None:
    row.assistant_message = MSG_PROGRESS[:4000]
    row.updated_at = utc_now()
