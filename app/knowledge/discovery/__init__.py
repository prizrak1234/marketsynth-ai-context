"""KB-WPL-01.8 Knowledge Discovery read models."""

from __future__ import annotations

from app.knowledge.discovery.contracts import BUNDLE_STATUS, CANONICAL_URI_BASE
from app.knowledge.discovery.explanations import explain_candidate, explain_route
from app.knowledge.discovery.queries import (
    discover,
    find_capabilities,
    find_error_patterns,
    find_patterns,
    find_practices,
    find_skills,
    route_task,
)
from app.knowledge.discovery.serialization import (
    FROZEN_DISCOVERY_BUNDLE_HASH,
    compute_result_hash,
    compute_semantic_bundle_hash,
    load_freeze_manifest,
)

__all__ = [
    "BUNDLE_STATUS",
    "CANONICAL_URI_BASE",
    "FROZEN_DISCOVERY_BUNDLE_HASH",
    "compute_result_hash",
    "compute_semantic_bundle_hash",
    "discover",
    "explain_candidate",
    "explain_route",
    "find_capabilities",
    "find_error_patterns",
    "find_patterns",
    "find_practices",
    "find_skills",
    "load_freeze_manifest",
    "route_task",
]
