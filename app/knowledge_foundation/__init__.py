"""Governed Knowledge Inventory foundation (Phase H2.1).

No bulk repository indexing. No embeddings unless storage option requires them.
"""

from app.knowledge_foundation.admission import (
    KNOWLEDGE_ADMISSION_RULES,
    can_admit_to_production,
    required_metadata_fields,
)
from app.knowledge_foundation.inventory import (
    filter_inventory,
    get_inventory_item,
    list_inventory,
)
from app.knowledge_foundation.retrieval_policy import (
    RETRIEVAL_ORDER,
    retrieve_for_skill,
)
from app.knowledge_foundation.scopes import (
    assert_retrieval_allowed,
    is_cross_tenant_denied,
)
from app.knowledge_foundation.storage_decision import (
    SELECTED_STORAGE_OPTION,
    STORAGE_DECISION_RATIONALE,
)

__all__ = [
    "KNOWLEDGE_ADMISSION_RULES",
    "RETRIEVAL_ORDER",
    "SELECTED_STORAGE_OPTION",
    "STORAGE_DECISION_RATIONALE",
    "assert_retrieval_allowed",
    "can_admit_to_production",
    "filter_inventory",
    "get_inventory_item",
    "is_cross_tenant_denied",
    "list_inventory",
    "required_metadata_fields",
    "retrieve_for_skill",
]
