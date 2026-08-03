"""GPTunnel CreativeLab video adapter — implements ImageVideoGateway for VIDEO modality."""

from __future__ import annotations

import asyncio
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.media_generation.gateway import (
    GatewayCreateRequest,
    GatewayCreateResult,
    GatewayInvokeStatus,
    GatewayModality,
    GatewayPollResult,
    ImageVideoGateway,
)
from app.video_studio.provider_duration_capabilities import provider_payload_duration_seconds


class GptunnelVideoGateway:
    """Async media/create + media/result for video models (i2v / t2v)."""

    code = "gptunnel_creativelab"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        key = settings.gptunnel_api_key
        if key is None or not key.get_secret_value().strip():
            raise InvalidStateError("GPTunnel API key is not configured")
        if not settings.video_generation_enabled:
            raise InvalidStateError("Video generation is disabled")

    @property
    def clients_connected(self) -> bool:
        return True

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._settings.gptunnel_api_key.get_secret_value().strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _base(self) -> str:
        return (self._settings.gptunnel_base_url or "https://gptunnel.ru/v1").rstrip("/") + "/"

    async def create(self, request: GatewayCreateRequest) -> GatewayCreateResult:
        if request.modality != GatewayModality.VIDEO:
            return GatewayCreateResult(
                status=GatewayInvokeStatus.BLOCKED,
                detail_code="wrong_modality",
                detail_ru="Адаптер GPTunnel video принимает только VIDEO.",
                paid_call_performed=False,
            )
        model = request.model or self._settings.gptunnel_video_model
        create_url = urljoin(self._base(), "media/create")
        payload: dict[str, object] = {
            "model": model,
            "prompt": request.prompt[:4000],
            "ar": request.aspect_ratio or "16:9",
        }
        if request.images:
            payload["images"] = list(request.images[:1])
        # GPTunnel CreativeLab Veo create does not accept duration — model default applies.
        _ = provider_payload_duration_seconds(model)
        _ = request.duration_seconds

        async with httpx.AsyncClient(timeout=120.0) as client:
            created = await client.post(create_url, headers=self._headers(), json=payload)
            if created.status_code >= 400:
                return GatewayCreateResult(
                    status=GatewayInvokeStatus.FAILED,
                    detail_code="gptunnel_create_failed",
                    detail_ru=f"GPTunnel create failed status={created.status_code}",
                    paid_call_performed=True,
                )
            body = created.json()
            task_id = body.get("id") or body.get("task_id")
            if not task_id:
                return GatewayCreateResult(
                    status=GatewayInvokeStatus.FAILED,
                    detail_code="gptunnel_no_task_id",
                    detail_ru="GPTunnel create returned no task id",
                    paid_call_performed=True,
                )
            return GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id=str(task_id),
                detail_code="queued",
                paid_call_performed=True,
            )

    async def poll(self, job_id: str) -> GatewayPollResult:
        result_url = urljoin(self._base(), "media/result")
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_status = ""
            body: dict[str, object] = {}
            for _ in range(40):
                polled = await client.post(
                    result_url,
                    headers=self._headers(),
                    json={"task_id": job_id},
                )
                if polled.status_code >= 400:
                    return GatewayPollResult(
                        status=GatewayInvokeStatus.FAILED,
                        detail_code="gptunnel_result_failed",
                        paid_call_performed=True,
                    )
                body = polled.json()
                last_status = str(body.get("status") or "")
                url = body.get("url")
                if url and last_status in {"done", "completed", "success"}:
                    mime = str(body.get("mime") or "video/mp4")
                    return GatewayPollResult(
                        status=GatewayInvokeStatus.DONE,
                        url=str(url),
                        mime=mime,
                        detail_code="done",
                        paid_call_performed=True,
                    )
                if last_status in {"failed", "error", "cancelled"}:
                    return GatewayPollResult(
                        status=GatewayInvokeStatus.FAILED,
                        detail_code=f"gptunnel_task_{last_status}",
                        paid_call_performed=True,
                    )
                await asyncio.sleep(1.5)
        return GatewayPollResult(
            status=GatewayInvokeStatus.FAILED,
            detail_code="gptunnel_poll_timeout",
            paid_call_performed=True,
        )


def try_build_gptunnel_video_gateway(settings: Settings) -> ImageVideoGateway | None:
    try:
        return GptunnelVideoGateway(settings)
    except InvalidStateError:
        return None
