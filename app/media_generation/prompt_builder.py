"""Build generation prompts from approved media briefs (Phase AI.56)."""

from __future__ import annotations

from app.core.security import sanitize_text
from app.db.models.media import MediaBriefTable


def build_image_prompt_from_brief(brief: MediaBriefTable) -> str:
    parts = [
        f"Title: {sanitize_text(brief.title)}",
        f"Goal: {sanitize_text(brief.goal)}",
        f"Audience: {sanitize_text(brief.target_audience)}",
        f"Platform: {sanitize_text(brief.platform)}",
        f"Creative direction: {sanitize_text(brief.creative_direction)}",
        f"Visual style: {sanitize_text(brief.visual_style)}",
        f"Composition: {sanitize_text(brief.composition)}",
    ]
    overlay = sanitize_text(brief.text_overlay).strip()
    if overlay:
        parts.append(f"Text overlay: {overlay}")
    return "\n".join(p for p in parts if p.split(": ", 1)[-1].strip())[:8000]
