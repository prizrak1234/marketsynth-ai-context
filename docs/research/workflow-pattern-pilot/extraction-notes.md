# Extraction Notes

## Abstraction method

1. Read frozen catalog metadata (categories, providers, functional_classes, side effects).
2. Identify architectural problem (approval, retry, RAG, etc.) — one problem per pattern.
3. Map observed node functional classes to provider-neutral steps.
4. Place integrated providers only in `implementation_variants`.
5. Attach source workflow IDs and workflow hashes from catalog.
6. Run source support gate and quality gates before `maturity=reviewed`.

## Provider neutrality

Main flow uses:

- `publication_target`, `message_channel`, `LLM_provider`, `storage_provider`
- `CRM_provider`, `approval_interface`, `evidence_store`, `transport`

Forbidden in neutral body: n8n node types, credential IDs, raw expressions.

## Non-execution boundary

- Source workflow JSON from intake **not** copied into patterns.
- No n8n import, no workflow execution, no Connector activation.
- Patterns are architectural documentation for manual review only.
