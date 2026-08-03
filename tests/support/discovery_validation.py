"""Test helpers for KB-WPL-01.8 discovery."""

from __future__ import annotations

from app.knowledge.discovery.serialization import (
    FROZEN_DISCOVERY_BUNDLE_HASH,
    compute_semantic_bundle_hash,
    load_freeze_manifest,
)

__all__ = [
    "FROZEN_DISCOVERY_BUNDLE_HASH",
    "compute_semantic_bundle_hash",
    "load_freeze_manifest",
]


def base_query(
    task_description: str,
    *,
    query_id: str = "test-query",
    tenant_id: str = "tenant-alpha",
    mode: str = "task_routing",
    execution_sensitivity: str = "none",
    **extra: object,
) -> dict:
    payload = {
        "query_id": query_id,
        "task_description": task_description,
        "tenant_id": tenant_id,
        "mode": mode,
        "execution_sensitivity": execution_sensitivity,
        "result_limit": 10,
        "provenance": {"origin": "test", "phase": "KB-WPL-01.8"},
    }
    payload.update(extra)
    return payload
