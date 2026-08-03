"""Deterministic read-only knowledge catalog search — KB-SKILL-01.7."""

from app.knowledge.catalog.contracts import CatalogSearchResult
from app.knowledge.catalog.errors import CatalogSearchError
from app.knowledge.catalog.indexes import build_artifact_index
from app.knowledge.catalog.queries import search_artifacts
from app.knowledge.catalog.visibility import filter_by_tenant, is_audit_mode

__all__ = [
    "CatalogSearchError",
    "CatalogSearchResult",
    "build_artifact_index",
    "filter_by_tenant",
    "is_audit_mode",
    "search_artifacts",
]
