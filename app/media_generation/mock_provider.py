"""Deterministic mock image provider — no external API (Phase AI.56)."""

from __future__ import annotations

import hashlib

from app.media_generation.contracts import ImageGenerationInput, ImageGenerationResult
from app.media_generation.safe_metadata import sanitize_generation_metadata


class MockImageGenerationProvider:
    provider_name = "mock"

    async def generate_image(self, input_data: ImageGenerationInput) -> ImageGenerationResult:
        digest = hashlib.sha256(input_data.prompt.encode("utf-8")).hexdigest()[:16]
        safe = sanitize_generation_metadata(
            {
                "provider": self.provider_name,
                "mock": True,
                "placeholder": True,
                "image_count": input_data.n,
                "size": input_data.size,
                "mime_type": "image/png",
            },
        )
        return ImageGenerationResult(
            provider=self.provider_name,
            safe_metadata=safe,
            provider_asset_ref=f"mock://image/{digest}",
            storage_uri=f"mock://storage/{digest}.png",
            mime_type="image/png",
            width=1024,
            height=1024,
        )
