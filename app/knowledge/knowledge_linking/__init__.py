"""KB-WPL-01.5 Knowledge Linking — non-executable validation."""

from __future__ import annotations

from app.knowledge.knowledge_linking.contracts import SKILL_ID, SKILL_VERSION
from app.knowledge.knowledge_linking.contradiction_detection import detect_contradiction_candidates
from app.knowledge.knowledge_linking.duplicate_detection import (
    classify_provider_variants,
    detect_duplicate_candidates,
)
from app.knowledge.knowledge_linking.orphan_detection import (
    collect_linked_artifact_ids,
    detect_orphan_artifacts,
)
from app.knowledge.knowledge_linking.relations import ALLOWED_RELATION_TYPES
from app.knowledge.knowledge_linking.supersession import detect_supersession_candidates
from app.knowledge.knowledge_linking.validation import (
    detect_broken_links,
    detect_index_recommendations,
    validate_knowledge_link,
    validate_knowledge_node,
    validate_linking_input,
    validate_linking_output,
)
from app.knowledge.knowledge_linking.visibility import (
    filter_visible_artifacts,
    generic_not_found_error,
    reject_cross_tenant_link,
)

__all__ = [
    "ALLOWED_RELATION_TYPES",
    "SKILL_ID",
    "SKILL_VERSION",
    "classify_provider_variants",
    "collect_linked_artifact_ids",
    "detect_broken_links",
    "detect_contradiction_candidates",
    "detect_duplicate_candidates",
    "detect_index_recommendations",
    "detect_orphan_artifacts",
    "detect_supersession_candidates",
    "filter_visible_artifacts",
    "generic_not_found_error",
    "reject_cross_tenant_link",
    "validate_knowledge_link",
    "validate_knowledge_node",
    "validate_linking_input",
    "validate_linking_output",
]
