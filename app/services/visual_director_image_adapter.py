"""Pin-aware image generation adapter for Visual Director (PRODUCT-CD-RUNTIME-02).

Domain layer never depends on provider brand names in user-facing copy.
Deterministic fixtures are opt-in via CONTENT_DIRECTOR_IMAGE_DETERMINISTIC only.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.media_generation.contracts import ImageGenerationInput
from app.media_generation.openai_images_provider import OpenAIImagesProvider
from app.media_generation.safe_metadata import sanitize_generation_metadata

_ASPECT_SIZES: dict[str, tuple[int, int, str]] = {
    "1:1": (1024, 1024, "1024x1024"),
    "16:9": (1792, 1024, "1792x1024"),
    "9:16": (1024, 1792, "1024x1792"),
}

_MIN_BYTES = 100
_MAX_BYTES = 25 * 1024 * 1024
_MOCK_MARKER = "marketsynth_diagnostic_placeholder_v1"
_SKILL_ID = "marketsynth.visual_generation"
_SKILL_VERSION = "1.0.0"


@dataclass(frozen=True)
class GeneratedImageCandidate:
    title: str
    image_bytes: bytes
    mime_type: str
    width: int
    height: int
    checksum: str
    provider: str
    model: str
    metadata: dict[str, Any]
    safety_result: str


def build_prompt_from_snapshot(snapshot_payload: dict[str, Any]) -> str:
    parts = [
        f"Objective: {snapshot_payload.get('objective') or ''}",
        f"Scene: {snapshot_payload.get('scene_description') or ''}",
        f"Subject: {snapshot_payload.get('subject') or ''}",
        f"Style: {snapshot_payload.get('style') or ''}",
        f"Audience: {snapshot_payload.get('audience') or ''}",
        f"Mood: {snapshot_payload.get('mood') or ''}",
    ]
    overlay = str(snapshot_payload.get("text_overlay") or "").strip()
    if overlay:
        parts.append(f"Text on image (exact): {overlay}")
    must_include = str(snapshot_payload.get("must_include") or "").strip()
    if must_include:
        parts.append(f"Must include: {must_include}")
    must_avoid = str(snapshot_payload.get("must_avoid") or "").strip()
    if must_avoid:
        parts.append(f"Must avoid: {must_avoid}")
    parts.append("Commercial social post image. No watermarks. High quality.")
    prompt = "\n".join(parts).strip()
    if len(prompt) < 20:
        raise InvalidStateError("prompt_too_short")
    if len(prompt) > 4000:
        prompt = prompt[:4000]
    return prompt


def validate_image_bytes(payload: bytes) -> tuple[str, int, int]:
    if len(payload) < _MIN_BYTES or len(payload) > _MAX_BYTES:
        raise InvalidStateError("invalid_image_payload")
    if _MOCK_MARKER.encode("utf-8") in payload:
        raise InvalidStateError("invalid_image_payload")
    if payload[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif payload[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise InvalidStateError("invalid_image_payload")
    width = height = 0
    try:
        from PIL import Image

        with Image.open(io.BytesIO(payload)) as img:
            width, height = img.size
    except Exception as exc:  # noqa: BLE001
        raise InvalidStateError("invalid_image_payload") from exc
    if width <= 0 or height <= 0:
        raise InvalidStateError("invalid_image_payload")
    return mime, width, height


def _fixture_png(*, seed: str, width: int, height: int, variant: int) -> bytes:
    """Deterministic E2E PNG — never used on commercial customer path."""
    from PIL import Image, ImageDraw

    digest = hashlib.sha256(f"{seed}:{variant}".encode("utf-8")).digest()
    bg = (30 + digest[0] % 60, 40 + digest[1] % 70, 80 + digest[2] % 90)
    accent = (160 + digest[3] % 60, 100 + digest[4] % 80, 70 + digest[5] % 100)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([32, 32, width - 32, height // 3], fill=accent)
    draw.ellipse(
        [width // 5, height // 3, width * 4 // 5, height * 4 // 5],
        fill=(min(255, bg[0] + 50), min(255, bg[1] + 40), min(255, bg[2] + 30)),
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class VisualDirectorImageAdapter:
    """Generate 1..N image candidates from a pinned VisualInputSnapshot only."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def generate_candidates(
        self,
        *,
        snapshot_payload: dict[str, Any],
        visual_request_id: str,
        visual_request_version: int,
        snapshot_id: str,
        requested_variants: int,
    ) -> list[GeneratedImageCandidate]:
        if requested_variants < 1 or requested_variants > 4:
            raise InvalidStateError("requested_variants must be between 1 and 4")

        if not snapshot_payload.get("visual_request_id"):
            raise InvalidStateError("Snapshot missing visual_request_id pin")
        if str(snapshot_payload.get("visual_request_id")) != str(visual_request_id):
            raise InvalidStateError("Snapshot visual_request_id mismatch")
        if int(snapshot_payload.get("visual_request_version", -1)) != int(
            visual_request_version
        ):
            raise InvalidStateError("Snapshot visual_request_version mismatch")

        if self._settings.content_director_image_deterministic:
            return self._deterministic_candidates(
                snapshot_payload=snapshot_payload,
                count=requested_variants,
            )

        return await self._provider_candidates(
            snapshot_payload=snapshot_payload,
            count=requested_variants,
            visual_request_id=visual_request_id,
            snapshot_id=snapshot_id,
        )

    def _deterministic_candidates(
        self,
        *,
        snapshot_payload: dict[str, Any],
        count: int,
    ) -> list[GeneratedImageCandidate]:
        aspect = str(snapshot_payload.get("aspect_ratio") or "1:1")
        width, height, _size = _ASPECT_SIZES.get(aspect, _ASPECT_SIZES["1:1"])
        title_base = str(snapshot_payload.get("title") or "Social image")
        seed = str(snapshot_payload.get("visual_request_id") or "seed")
        out: list[GeneratedImageCandidate] = []
        for idx in range(count):
            n = idx + 1
            payload = _fixture_png(seed=seed, width=width, height=height, variant=n)
            mime, w, h = validate_image_bytes(payload)
            checksum = "sha256:" + hashlib.sha256(payload).hexdigest()
            out.append(
                GeneratedImageCandidate(
                    title=f"{title_base} — вариант {n}",
                    image_bytes=payload,
                    mime_type=mime,
                    width=w,
                    height=h,
                    checksum=checksum,
                    provider="deterministic",
                    model="fixture",
                    metadata={
                        **sanitize_generation_metadata(
                            {
                                "adapter": "visual_director_image",
                                "deterministic": True,
                                "visual_request_version": snapshot_payload.get(
                                    "visual_request_version"
                                ),
                            }
                        ),
                        "skill_id": _SKILL_ID,
                        "skill_version": _SKILL_VERSION,
                        "adapter": "visual_director_image",
                    },
                    safety_result="passed",
                )
            )
        return out

    async def _provider_candidates(
        self,
        *,
        snapshot_payload: dict[str, Any],
        count: int,
        visual_request_id: str,
        snapshot_id: str,
    ) -> list[GeneratedImageCandidate]:
        if not self._settings.image_generation_enabled:
            raise InvalidStateError("provider_config_error: image generation disabled")

        provider_name = (self._settings.image_generation_provider or "").strip().lower()
        if provider_name != "openai_images":
            raise InvalidStateError("provider_config_error: unsupported image provider")

        api_key = self._settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise InvalidStateError("provider_config_error: image provider not configured")

        try:
            provider = OpenAIImagesProvider(self._settings, allow_h26a_gate=True)
        except InvalidStateError as exc:
            raise InvalidStateError(f"provider_config_error: {exc}") from exc

        prompt = build_prompt_from_snapshot(snapshot_payload)
        # Blocked-prompt heuristic (minimal content policy)
        blocked_terms = ("child sexual", "csam", "explicit minor")
        lowered = prompt.lower()
        if any(term in lowered for term in blocked_terms):
            raise InvalidStateError("policy_rejected")

        aspect = str(snapshot_payload.get("aspect_ratio") or "1:1")
        if aspect not in _ASPECT_SIZES:
            raise InvalidStateError("unsupported_aspect_ratio")
        width, height, size = _ASPECT_SIZES[aspect]
        title_base = str(snapshot_payload.get("title") or "Social image")
        model = self._settings.openai_images_model or "gpt-image-1"

        out: list[GeneratedImageCandidate] = []
        for idx in range(count):
            n = idx + 1
            try:
                result = await provider.generate_image(
                    ImageGenerationInput(
                        prompt=prompt,
                        size=size,
                        n=1,
                        model=model,
                    )
                )
            except InvalidStateError as exc:
                detail = str(exc).lower()
                if "policy" in detail or "safety" in detail:
                    raise InvalidStateError("policy_rejected") from exc
                raise InvalidStateError("provider_failure") from exc
            except Exception as exc:  # noqa: BLE001
                raise InvalidStateError("provider_failure") from exc

            image_bytes = result.image_bytes
            if not image_bytes and result.provider_asset_ref:
                # Download URL if provider returned URL only (no secrets persisted)
                import httpx

                try:
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        resp = await client.get(str(result.provider_asset_ref))
                        resp.raise_for_status()
                        image_bytes = resp.content
                except Exception as exc:  # noqa: BLE001
                    raise InvalidStateError("provider_failure") from exc

            if not image_bytes:
                raise InvalidStateError("provider_failure")

            mime, w, h = validate_image_bytes(image_bytes)
            checksum = "sha256:" + hashlib.sha256(image_bytes).hexdigest()
            safe = sanitize_generation_metadata(
                {
                    **(result.safe_metadata or {}),
                    "visual_request_id": visual_request_id,
                    "snapshot_id": snapshot_id,
                    "candidate_index": n,
                }
            )
            # Explicitly strip any URL-like keys; stamp skill outside allowlist merge
            for key in list(safe.keys()):
                if "url" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                    safe.pop(key, None)
            safe = {
                **safe,
                "skill_id": _SKILL_ID,
                "skill_version": _SKILL_VERSION,
                "adapter": "visual_director_image",
            }

            out.append(
                GeneratedImageCandidate(
                    title=f"{title_base} — вариант {n}",
                    image_bytes=image_bytes,
                    mime_type=mime,
                    width=w or width,
                    height=h or height,
                    checksum=checksum,
                    provider="image_adapter",
                    model=model,
                    metadata=safe,
                    safety_result="passed",
                )
            )
        return out


def resolve_storage_path(
    *,
    settings: Settings,
    owner_id: UUID,
    project_id: UUID,
    asset_id: UUID,
    version: int,
    mime_type: str,
) -> str:
    ext = ".png"
    if mime_type == "image/jpeg":
        ext = ".jpg"
    elif mime_type == "image/webp":
        ext = ".webp"
    root = settings.image_generation_storage_dir.strip() or "data/generated_visuals"
    return (
        f"{root}/cd-image/{owner_id}/{project_id}/{asset_id}/v{version}{ext}"
    )
