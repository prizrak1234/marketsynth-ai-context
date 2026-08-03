"""Higgsfield connector identifiers — canonical operations only (CONN-HF-01.1)."""

from __future__ import annotations

HIGGSFIELD_CONNECTOR_ID = "connector.higgsfield"
HIGGSFIELD_CONNECTOR_VERSION = "0.1.0"
HIGGSFIELD_CONNECTOR_VERIFICATION_STATUS = "sandbox_verification_required"
HIGGSFIELD_OFFICIAL_MCP_ENDPOINT = "https://mcp.higgsfield.ai/mcp"

# Canonical Marketsynth media operations — internal contract, not MCP tool names.
MEDIA_OP_IMAGE_GENERATE = "media.image.generate"
MEDIA_OP_VIDEO_GENERATE = "media.video.generate"
MEDIA_OP_JOB_GET_STATUS = "media.job.get_status"
MEDIA_OP_ASSET_FETCH = "media.asset.fetch"

MEDIA_CANONICAL_OPERATIONS: frozenset[str] = frozenset(
    {
        MEDIA_OP_IMAGE_GENERATE,
        MEDIA_OP_VIDEO_GENERATE,
        MEDIA_OP_JOB_GET_STATUS,
        MEDIA_OP_ASSET_FETCH,
    }
)

MEDIA_RENDER_OPERATIONS: frozenset[str] = frozenset(
    {
        MEDIA_OP_IMAGE_GENERATE,
        MEDIA_OP_VIDEO_GENERATE,
    }
)

# Upstream Skills allowed to invoke the renderer (spec must be complete).
RENDERER_UPSTREAM_SKILL_IDS: frozenset[str] = frozenset(
    {
        "ms.skill.presentation_architecture",
        "ms.skill.image_generation_spec",
        "ms.skill.visual_brief",
        "ms.skill.storyboard",
    }
)

# Deprecated guessed connector tool IDs from CONN-HF-01 candidate — not authoritative.
DEPRECATED_GUESSED_TOOL_IDS: frozenset[str] = frozenset(
    {
        "higgsfield.render_image",
        "higgsfield.render_video",
        "higgsfield.get_generation_status",
        "higgsfield.download_result",
    }
)
