"""Owner-only canonical video acceptance preview — read-only smoke lineage binding."""

from __future__ import annotations

from uuid import UUID

# VS.2A smoke clip lineage (do not mutate owner_id or copy assets).
CANONICAL_CLIP_REQUEST_ID = UUID("b3ad1909-dafd-4440-8968-345b3717093b")
CANONICAL_SOURCE_IMAGE_ASSET_ID = UUID("764a23b8-3d56-4d8a-a41e-4a484f0f47bb")
CANONICAL_RESULT_ASSET_ID = UUID("927583e5-e95c-4cb7-92a8-d480cbdeef24")

_CANONICAL_ASSET_IDS = frozenset(
    {
        CANONICAL_SOURCE_IMAGE_ASSET_ID,
        CANONICAL_RESULT_ASSET_ID,
    }
)


def is_canonical_owner_preview_asset(asset_id: UUID) -> bool:
    return asset_id in _CANONICAL_ASSET_IDS
