"""KG.2 package — operational governance (no VectorDB / no parallel Runtime)."""

from app.knowledge_governance.lifecycle import LifecycleError, assert_transition
from app.knowledge_governance.governed_snapshot import (
    InsufficientGovernedKnowledgeError,
    create_governed_snapshot,
)

__all__ = [
    "LifecycleError",
    "assert_transition",
    "InsufficientGovernedKnowledgeError",
    "create_governed_snapshot",
]
