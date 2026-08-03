"""OpenAI Images provider — gated, safe metadata only (Phase AI.57)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.media_generation.contracts import ImageGenerationInput, ImageGenerationResult
from app.media_generation.safe_metadata import sanitize_generation_metadata


class OpenAIImagesProvider:
    """Lazy-imports OpenAI SDK; never persists raw API payloads."""

    provider_name = "openai_images"

    def __init__(self, settings: Settings, *, allow_h26a_gate: bool = False) -> None:
        self._settings = settings
        api_key = settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise InvalidStateError("OpenAI API key is not configured")
        media_ok = bool(settings.media_generation_enabled and settings.openai_images_enabled)
        h26a_ok = bool(
            allow_h26a_gate
            and settings.image_generation_enabled
            and (settings.image_generation_provider or "").strip().lower() == "openai_images"
        )
        if not (media_ok or h26a_ok):
            raise InvalidStateError("OpenAI Images provider is disabled")

    async def generate_image(self, input_data: ImageGenerationInput) -> ImageGenerationResult:
        import base64

        from openai import AsyncOpenAI

        model = input_data.model or self._settings.openai_images_model
        client = AsyncOpenAI(api_key=self._settings.openai_api_key.get_secret_value())
        response = await client.images.generate(
            model=model,
            prompt=input_data.prompt[:4000],
            size=input_data.size,
            n=min(input_data.n, 1),
        )
        first = response.data[0] if response.data else None
        revised = getattr(first, "revised_prompt", None) if first else None
        url_ref = getattr(first, "url", None) if first else None
        image_bytes: bytes | None = None
        b64 = getattr(first, "b64_json", None) if first else None
        if b64:
            image_bytes = base64.b64decode(str(b64))
        safe = sanitize_generation_metadata(
            {
                "provider": self.provider_name,
                "model": model,
                "image_count": 1,
                "size": input_data.size,
                "mime_type": "image/png",
                "has_b64": bool(image_bytes),
            },
        )
        if revised:
            safe["revision"] = str(revised)[:512]
        provider_ref = str(url_ref)[:512] if url_ref else None
        return ImageGenerationResult(
            provider=self.provider_name,
            safe_metadata=safe,
            provider_asset_ref=provider_ref,
            storage_uri=None,
            mime_type="image/png",
            width=_parse_dimension(input_data.size, index=0),
            height=_parse_dimension(input_data.size, index=1),
            image_bytes=image_bytes,
        )

    async def edit_with_reference(
        self,
        *,
        prompt: str,
        image_path: str,
        size: str = "1024x1024",
        preservation_instructions: str = "",
    ) -> ImageGenerationResult:
        """Reference-guided edit using primary image. Never dumps raw payloads."""
        from openai import AsyncOpenAI
        from pathlib import Path

        model = self._settings.openai_images_model
        client = AsyncOpenAI(api_key=self._settings.openai_api_key.get_secret_value())
        full_prompt = (prompt + "\n" + preservation_instructions).strip()[:4000]
        path = Path(image_path)
        if not path.is_file():
            raise InvalidStateError("Reference image file missing")
        # images.edit — model-dependent; use file handle
        import base64

        with path.open("rb") as fh:
            try:
                edit_model = (
                    model
                    if str(model).startswith("gpt-image") or str(model).startswith("dall-e-2")
                    else "gpt-image-1"
                )
                response = await client.images.edit(
                    model=edit_model,
                    image=fh,
                    prompt=full_prompt,
                    size=size if size in {"256x256", "512x512", "1024x1024"} else "1024x1024",
                    n=1,
                )
            except Exception:
                # Fallback: some orgs only allow generate — re-raise for caller mapping
                raise
        first = response.data[0] if response.data else None
        url_ref = getattr(first, "url", None) if first else None
        image_bytes: bytes | None = None
        b64 = getattr(first, "b64_json", None) if first else None
        if b64:
            image_bytes = base64.b64decode(str(b64))
        safe = sanitize_generation_metadata(
            {
                "provider": self.provider_name,
                "model": model,
                "image_count": 1,
                "size": size,
                "mime_type": "image/png",
                "mode": "reference_guided",
                "has_b64": bool(image_bytes),
                # OpenAI Images responses expose `id` when available — lineage only.
                "provider_request_id": (
                    str(getattr(response, "id", None) or getattr(response, "created", "") or "")
                    or None
                ),
            },
        )
        if safe.get("provider_request_id") in {None, "", "None"}:
            safe.pop("provider_request_id", None)
        return ImageGenerationResult(
            provider=self.provider_name,
            safe_metadata=safe,
            provider_asset_ref=str(url_ref)[:512] if url_ref else None,
            storage_uri=None,
            mime_type="image/png",
            width=_parse_dimension(size, index=0),
            height=_parse_dimension(size, index=1),
            image_bytes=image_bytes,
        )


def _parse_dimension(size: str, *, index: int) -> int | None:
    parts = size.lower().split("x")
    if len(parts) != 2:
        return None
    try:
        return int(parts[index])
    except ValueError:
        return None
