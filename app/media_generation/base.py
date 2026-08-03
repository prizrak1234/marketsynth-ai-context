"""Media generation provider interface (Phase AI.56)."""

from __future__ import annotations

from typing import Protocol

from app.media_generation.contracts import ImageGenerationInput, ImageGenerationResult


class ImageGenerationProvider(Protocol):
    """Image generation only — video contract deferred."""

    provider_name: str

    async def generate_image(self, input_data: ImageGenerationInput) -> ImageGenerationResult:
        """Generate or simulate an image; return safe metadata only."""
