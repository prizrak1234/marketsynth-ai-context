"""Storage decision for Knowledge Foundation (Phase H2.1)."""

from __future__ import annotations

from app.schemas.contracts import KnowledgeStorageOption

# Prefer PostgreSQL metadata + full-text search for the first controlled version.
SELECTED_STORAGE_OPTION = KnowledgeStorageOption.POSTGRES_FTS

STORAGE_DECISION_RATIONALE = (
    "Option A selected: PostgreSQL stores KnowledgeItem metadata; full-text search "
    "covers allowlisted approved content. Vector indexes (Option B) stay behind a "
    "future adapter only if semantic retrieval is demonstrably required. "
    "No embeddings are created in H2.1–H2.2. Existing Source/Evidence remain the "
    "provenance path for investigation facts; they are not replaced by a parallel RAG dump."
)

EMBEDDINGS_ENABLED = False
BULK_REPO_INGESTION_ENABLED = False
PARALLEL_RUNTIME_ENABLED = False
