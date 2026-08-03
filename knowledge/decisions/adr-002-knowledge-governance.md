# ADR-002: Knowledge Governance Architecture

**Date:** 2026  
**Status:** Accepted  
**Canonical doc:** [docs/architecture/adr_knowledge_governance.md](../../docs/architecture/adr_knowledge_governance.md)

## Context

Agent answers need traceable evidence without a VectorDB hallucination layer in v1.

## Decision

Implement Knowledge Governance (KG.1 architecture + KG.2 ops) with:
- Citation Contract: Answer + Evidence + Source + Confidence
- Governed KnowledgeSnapshots for specialist attachment
- `insufficient_governed_knowledge` block for industrial domains without fresh published snapshots
- No VectorDB as default retrieval layer in v1

## Alternatives considered

- RAG/VectorDB first — deferred
- Unstructured prompt injection — rejected

## Consequences

- `app/knowledge/` runtime modules for discovery, catalog, linking
- Knowledge-backed answers must cite sources
- Industrial specialist attachment strictly gated

## Verification

Knowledge governance routes + KG docs; compliance matrix audit
