"""Image generation mock tool service (Phase AI.220)."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from app.core.security import sanitize_text
from app.schemas.contracts import ImageGenerationToolInput


class MarketingImageGenerationService:
    """Mock image generation — max one image, no external provider calls."""

    async def execute(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        parsed = ImageGenerationToolInput.model_validate(payload)
        prompt = sanitize_text(parsed.prompt).strip()
        if not prompt:
            raise ValueError("prompt is required")

        aspect_ratio = parsed.aspect_ratio or "1:1"
        image_size = parsed.image_size or "1024x1024"
        image_id = uuid4()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]

        output = {
            "provider": "mock",
            "prompt_preview": prompt[:160],
            "images": [
                {
                    "url": f"mock://image/{image_id}",
                    "aspect_ratio": aspect_ratio,
                    "size": image_size,
                },
            ],
        }
        metadata = {
            "provider": "mock",
            "external_call": False,
            "image_count": 1,
            "prompt_hash": prompt_hash,
        }
        return output, metadata
