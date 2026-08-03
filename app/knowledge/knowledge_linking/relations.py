"""Finite relation taxonomy for Knowledge Linking."""

from __future__ import annotations

ALLOWED_RELATION_TYPES = frozenset(
    {
        "related_to",
        "depends_on",
        "derived_from",
        "adapted_from",
        "supersedes",
        "superseded_by",
        "contradicts",
        "implements",
        "documents",
        "example_of",
        "failure_of",
        "solution_for",
        "requires",
        "produces",
        "consumes",
        "validates",
        "validated_by",
        "rejected_by",
        "variant_of",
        "version_of",
        "governed_by",
        "audited_by",
        "mapped_to_capability",
        "uses_pattern",
        "uses_practice",
        "references_schema",
        "supported_by_evidence",
        "blocks",
        "blocked_by",
    }
)

ALLOWED_LINK_DIRECTIONS = frozenset({"forward", "reverse", "bidirectional"})

ALLOWED_CONFIDENCE = frozenset({"high", "medium", "low", "unknown"})

DETERMINISTIC_EVIDENCE_TYPES = frozenset(
    {
        "explicit_reference",
        "shared_immutable_identity",
        "declared_dependency",
        "lineage_edge",
        "manifest_reference",
        "audit_reference",
        "schema_reference",
        "capability_binding",
        "source_provenance",
        "deterministic_title_version_match",
        "structurally_equivalent_pattern",
        "explicit_contradiction_evidence",
    }
)
