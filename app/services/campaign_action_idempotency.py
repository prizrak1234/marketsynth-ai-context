"""Campaign action idempotency replay cache (Phase AI.173)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.executors.idempotency import normalize_idempotency_key
from app.schemas.contracts import CampaignActionResult, CampaignActionResultStatus, CampaignActionType, CampaignNextAction

_REPLAY_KEY = "action_replay_cache"
_MAX_ENTRIES = 32


def hash_idempotency_key(raw: str | None) -> str | None:
    normalized = normalize_idempotency_key(raw)
    if normalized is None:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def build_state_fingerprint(parts: list[str]) -> str:
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _result_to_dict(result: CampaignActionResult) -> dict[str, Any]:
    return result.model_dump(mode="json")


def _result_from_dict(data: dict[str, Any]) -> CampaignActionResult:
    return CampaignActionResult.model_validate(data)


def lookup_replay(
    metadata: dict[str, Any],
    *,
    key_hash: str,
    state_fingerprint: str,
) -> CampaignActionResult | None:
    cache = dict(metadata.get(_REPLAY_KEY) or {})
    entry = cache.get(key_hash)
    if not isinstance(entry, dict):
        return None
    if entry.get("state_fingerprint") != state_fingerprint:
        raise ValueError("idempotency_state_conflict")
    stored = entry.get("result")
    if not isinstance(stored, dict):
        return None
    return _result_from_dict(stored)


def store_replay(
    metadata: dict[str, Any],
    *,
    key_hash: str,
    state_fingerprint: str,
    result: CampaignActionResult,
) -> dict[str, Any]:
    cache = dict(metadata.get(_REPLAY_KEY) or {})
    cache[key_hash] = {
        "state_fingerprint": state_fingerprint,
        "result": _result_to_dict(result),
    }
    if len(cache) > _MAX_ENTRIES:
        oldest = next(iter(cache))
        cache.pop(oldest, None)
    merged = dict(metadata)
    merged[_REPLAY_KEY] = cache
    return merged


def already_applied_result(
    action_type: CampaignActionType,
    *,
    message: str,
    next_action: CampaignNextAction,
    updated_resource_type: str | None = None,
    updated_resource_id: Any = None,
) -> CampaignActionResult:
    return CampaignActionResult(
        status=CampaignActionResultStatus.ALREADY_APPLIED,
        message=message,
        action_type=action_type,
        updated_resource_type=updated_resource_type,
        updated_resource_id=updated_resource_id,
        next_action_after=next_action,
    )
