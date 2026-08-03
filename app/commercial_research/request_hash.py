"""Deterministic request hash for commercial research lineage."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID


def compute_commercial_research_request_hash(
    *,
    user_request_id: UUID,
    normalized_text: str,
    route_category: str,
    project_brief_fingerprint: str,
    project_brief_version: int,
) -> str:
    payload = "|".join(
        [
            str(user_request_id),
            normalized_text.strip(),
            route_category.strip(),
            project_brief_fingerprint.strip(),
            str(project_brief_version),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_skill_inputs_hash(skill_inputs: dict[str, Any] | None) -> str:
    if not skill_inputs:
        return ""
    normalized = json.dumps(skill_inputs, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
