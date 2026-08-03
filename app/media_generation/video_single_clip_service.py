"""VS.2 — single-clip Video Studio orchestration (Preview → Approve → Generate)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.media_generation.gateway import GatewayCreateRequest, GatewayInvokeStatus, GatewayModality
from app.media_generation.scene_graph import SceneGraph, VideoSceneMode, build_single_clip_scene_graph
from app.media_generation.video_readiness import image_to_video_live_verified
from app.media_generation.video_router import VideoCostQuoteBundle, VideoRouter, build_video_router


@dataclass(slots=True)
class SingleClipPreview:
    scene_graph: SceneGraph
    cost_quotes: VideoCostQuoteBundle
    ready_to_generate: bool
    blocked_reason_ru: str | None


@dataclass(slots=True)
class SingleClipResult:
    provider_code: str
    job_id: str | None
    status: str
    detail_code: str
    paid_call_performed: bool
    result_url: str | None = None
    mime: str | None = None
    scene_graph: SceneGraph | None = None


def _motion_in_prompt(prompt: str, camera_motion: str) -> str:
    motion = camera_motion.strip()
    if not motion:
        return prompt
    return f"{prompt}\n\nCamera motion: {motion}"


class VideoSingleClipService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._router: VideoRouter = build_video_router(settings)

    def preview_text_to_video(
        self,
        *,
        brief: str,
        duration_seconds: int = 8,
        aspect_ratio: str = "16:9",
        camera_motion: str = "",
    ) -> SingleClipPreview:
        graph = build_single_clip_scene_graph(
            brief=brief,
            mode=VideoSceneMode.TEXT_TO_VIDEO,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            camera_motion=camera_motion,
        )
        return self._preview(graph)

    def preview_image_to_video(
        self,
        *,
        brief: str,
        start_frame_url: str,
        duration_seconds: int = 8,
        aspect_ratio: str = "16:9",
        camera_motion: str = "",
    ) -> SingleClipPreview:
        graph = build_single_clip_scene_graph(
            brief=brief,
            mode=VideoSceneMode.IMAGE_TO_VIDEO,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            camera_motion=camera_motion,
        )
        graph.scenes[0].metadata["start_frame_url"] = start_frame_url
        return self._preview(graph)

    def _preview(self, graph: SceneGraph) -> SingleClipPreview:
        quotes = self._router.quote(modality=GatewayModality.VIDEO)
        ready = self._router.any_connected and image_to_video_live_verified(self._settings)
        blocked: str | None = None
        if not self._router.any_connected:
            blocked = "Видеодвижок ещё не подключён."
        elif not image_to_video_live_verified(self._settings):
            blocked = "Генерация видео будет доступна после проверки видеодвижка."
        return SingleClipPreview(
            scene_graph=graph,
            cost_quotes=quotes,
            ready_to_generate=ready,
            blocked_reason_ru=blocked,
        )

    async def generate_from_preview(
        self,
        preview: SingleClipPreview,
        *,
        approved: bool,
    ) -> SingleClipResult:
        if not approved:
            return SingleClipResult(
                provider_code="none",
                job_id=None,
                status="blocked",
                detail_code="approval_required",
                paid_call_performed=False,
            )
        if not preview.ready_to_generate:
            return SingleClipResult(
                provider_code="none",
                job_id=None,
                status="blocked",
                detail_code="not_ready",
                paid_call_performed=False,
            )
        scene = preview.scene_graph.scenes[0]
        prompt = _motion_in_prompt(scene.prompt, scene.camera_motion)
        images: list[str] = []
        if preview.scene_graph.mode == VideoSceneMode.IMAGE_TO_VIDEO:
            url = scene.metadata.get("start_frame_url")
            if isinstance(url, str) and url.strip():
                images = [url.strip()]
        request = GatewayCreateRequest(
            modality=GatewayModality.VIDEO,
            model=self._settings.gptunnel_video_model,
            prompt=prompt,
            aspect_ratio=scene.aspect_ratio,
            images=images,
            metadata={"scene_id": scene.scene_id, "mode": preview.scene_graph.mode.value},
        )
        provider_code, created = await self._router.create(request)
        if created.status != GatewayInvokeStatus.QUEUED or not created.job_id:
            return SingleClipResult(
                provider_code=provider_code,
                job_id=created.job_id,
                status=created.status.value,
                detail_code=created.detail_code,
                paid_call_performed=created.paid_call_performed,
                scene_graph=preview.scene_graph,
            )
        polled = await self._router.poll(provider_code, created.job_id)
        scene.provider_code = provider_code
        if polled.status == GatewayInvokeStatus.DONE and polled.url:
            scene.clip_asset_id = hashlib.sha256(polled.url.encode()).hexdigest()[:16]
            scene.metadata["result_url_hint"] = polled.url[:80] + "…"
        return SingleClipResult(
            provider_code=provider_code,
            job_id=created.job_id,
            status=polled.status.value,
            detail_code=polled.detail_code,
            paid_call_performed=polled.paid_call_performed or created.paid_call_performed,
            result_url=polled.url,
            mime=polled.mime,
            scene_graph=preview.scene_graph,
        )


def preview_to_safe_dict(preview: SingleClipPreview) -> dict[str, Any]:
    return {
        "scene_graph": preview.scene_graph.to_safe_dict(),
        "cost_quotes": {
            "recommendation": preview.cost_quotes.recommendation_display_name,
            "recommendation_reason_ru": preview.cost_quotes.recommendation_reason_ru,
            "quotes": [
                {
                    "display_name": q.display_name,
                    "connected": q.connected,
                    "estimated_cost_units": q.estimated_cost_units,
                    "recommended": q.recommended,
                }
                for q in preview.cost_quotes.quotes
            ],
        },
        "ready_to_generate": preview.ready_to_generate,
        "blocked_reason_ru": preview.blocked_reason_ru,
        "approval_required": True,
    }
