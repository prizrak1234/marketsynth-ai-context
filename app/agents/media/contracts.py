"""Media domain contracts (Phase AI.17) — visual consultation skeleton only."""

from __future__ import annotations

from enum import StrEnum

# Tool name substrings forbidden for Media (no generation, design tools, file I/O).
MEDIA_FORBIDDEN_TOOL_MARKERS: frozenset[str] = frozenset(
    {
        "image.generate",
        "image_generate",
        "video.generate",
        "video_generate",
        "canva",
        "figma",
        "heygen",
        "dall-e",
        "dalle",
        "midjourney",
        "stable.diffusion",
        "filesystem",
        "file.write",
        "file_write",
        "upload",
        "download",
        "secret",
        "shell",
        "deploy",
    },
)


class MediaOutputKind(StrEnum):
    """Structured media run output (in-memory only in AI.17)."""

    CONSULTATION = "consultation"
    VISUAL_BRIEF = "visual_brief"
