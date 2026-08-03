"""GPTunnel CreativeLab image provider (H2.6A alternate / fallback).

Uses async media/create + media/result. Never logs API keys or raw payloads.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.media_generation.contracts import ImageGenerationInput, ImageGenerationResult
from app.media_generation.safe_metadata import sanitize_generation_metadata

_AR_FROM_SIZE = {
    "1024x1024": "1:1",
    "1792x1024": "16:9",
    "1024x1792": "9:16",
}


class GptunnelImagesProvider:
    provider_name = "gptunnel"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        key = settings.gptunnel_api_key
        if key is None or not key.get_secret_value().strip():
            raise InvalidStateError("GPTunnel API key is not configured")
        if not settings.image_generation_enabled:
            raise InvalidStateError("Image generation is disabled")

    def _headers(self) -> dict[str, str]:
        # GPTunnel docs use Authorization: <api_key> (no Bearer prefix).
        return {
            "Authorization": self._settings.gptunnel_api_key.get_secret_value().strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _base(self) -> str:
        return (self._settings.gptunnel_base_url or "https://gptunnel.ru/v1").rstrip("/") + "/"

    async def generate_image(self, input_data: ImageGenerationInput) -> ImageGenerationResult:
        model = input_data.model or self._settings.gptunnel_images_model or "gpt-image-1"
        ar = _AR_FROM_SIZE.get(input_data.size, "1:1")
        create_url = urljoin(self._base(), "media/create")
        result_url = urljoin(self._base(), "media/result")

        async with httpx.AsyncClient(timeout=120.0) as client:
            created = await client.post(
                create_url,
                headers=self._headers(),
                json={
                    "model": model,
                    "prompt": input_data.prompt[:4000],
                    "ar": ar,
                },
            )
            if created.status_code >= 400:
                raise InvalidStateError(
                    f"GPTunnel create failed status={created.status_code}"
                )
            body = created.json()
            task_id = body.get("id") or body.get("task_id")
            if not task_id:
                raise InvalidStateError("GPTunnel create returned no task id")

            image_url: str | None = None
            last_status = str(body.get("status") or "")
            # Poll result (controlled, bounded)
            for _ in range(40):
                if body.get("url") and last_status in {"done", "completed", "success"}:
                    image_url = str(body["url"])
                    break
                await asyncio.sleep(1.5)
                polled = await client.post(
                    result_url,
                    headers=self._headers(),
                    json={"task_id": task_id},
                )
                if polled.status_code >= 400:
                    raise InvalidStateError(
                        f"GPTunnel result failed status={polled.status_code}"
                    )
                body = polled.json()
                last_status = str(body.get("status") or "")
                if body.get("url") and last_status in {"done", "completed", "success"}:
                    image_url = str(body["url"])
                    break
                if last_status in {"failed", "error", "cancelled"}:
                    raise InvalidStateError(f"GPTunnel task {last_status}")

            if not image_url:
                raise InvalidStateError("GPTunnel result timed out without url")

            # Download immediately — GPTunnel URLs expire (~48h).
            dl = await client.get(image_url, timeout=90.0)
            dl.raise_for_status()
            image_bytes = dl.content

        mime = "image/webp" if image_bytes[:4] == b"RIFF" else "image/png"
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            mime = "image/png"
        elif image_bytes[:2] == b"\xff\xd8":
            mime = "image/jpeg"

        safe = sanitize_generation_metadata(
            {
                "provider": self.provider_name,
                "model": model,
                "image_count": 1,
                "size": input_data.size,
                "mime_type": mime,
                "mode": "text_to_image",
                "has_b64": False,
            },
        )
        return ImageGenerationResult(
            provider=self.provider_name,
            safe_metadata=safe,
            provider_asset_ref=None,  # ephemeral URL — bytes already fetched
            storage_uri=None,
            mime_type=mime,
            width=_parse_dimension(input_data.size, 0),
            height=_parse_dimension(input_data.size, 1),
            image_bytes=image_bytes,
        )


def _parse_dimension(size: str, index: int) -> int | None:
    parts = size.lower().split("x")
    if len(parts) != 2:
        return None
    try:
        return int(parts[index])
    except ValueError:
        return None
