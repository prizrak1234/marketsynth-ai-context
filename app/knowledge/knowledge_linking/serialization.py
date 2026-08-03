"""Serialization helpers for Knowledge Linking."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_artifact_index(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {artifact["artifact_id"]: artifact for artifact in artifacts}
