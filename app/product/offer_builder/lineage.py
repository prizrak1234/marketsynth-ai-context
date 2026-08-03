"""Offer lineage metadata helpers."""

from __future__ import annotations

from typing import Any
from uuid import UUID


def build_lineage_metadata(
    *,
    project_id: UUID,
    launch_pack_request_id: UUID,
    business_verdict_id: UUID,
    upstream_refs: dict[str, Any],
    generation_request_id: UUID,
    version_number: int,
    revision_of_id: UUID | None = None,
) -> dict[str, Any]:
    return {
        "project_id": str(project_id),
        "launch_pack_request_id": str(launch_pack_request_id),
        "business_verdict_id": str(business_verdict_id),
        "generation_request_id": str(generation_request_id),
        "version_number": version_number,
        "revision_of_id": str(revision_of_id) if revision_of_id else None,
        "upstream_refs": upstream_refs,
    }
