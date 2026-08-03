"""Test helpers for KB-WPL-01.7 capability mapping."""

from __future__ import annotations

from pathlib import Path

from app.knowledge.capability_model.serialization import (
    BUNDLE_ROOT,
    FROZEN_CAPABILITY_MODEL_BUNDLE_HASH,
    FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH,
    compute_semantic_bundle_hash,
    load_freeze_manifest,
    recompute_freeze_manifest_bundle_hash,
)

REPO = Path(__file__).resolve().parents[2]

__all__ = [
    "BUNDLE_ROOT",
    "FROZEN_CAPABILITY_MODEL_BUNDLE_HASH",
    "FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH",
    "compute_semantic_bundle_hash",
    "load_freeze_manifest",
    "recompute_freeze_manifest_bundle_hash",
]
