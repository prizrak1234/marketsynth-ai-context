"""Payload snapshot hashing for tamper detection (Phase AI.68)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_snapshot_hash(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_snapshot_integrity(
    snapshot: dict[str, Any],
    stored_hash: str | None,
) -> bool:
    if not stored_hash:
        return False
    return compute_snapshot_hash(snapshot) == stored_hash
