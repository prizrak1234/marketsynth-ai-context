# Integration Registry

Authoritative view of external integrations. Credential presence never implies
capability. Source of truth: `app/integrations/registry.py`.

## Statuses

| Status | Meaning |
| --- | --- |
| configured | Key/token present; not yet ready for skill use |
| ready | Safe to use through a normalized BusinessTool |
| degraded | Partially available |
| blocked | Must not be used (n8n SSL/API mismatch) |
| disabled | Policy-disabled (Pinecone) |

## Current inventory (H2.7)

- **OpenAI / OpenRouter / GPTunnel** — LLM / image; ready when key present
- **Firecrawl / XMLRiver** — read-only research; configured after smoke
- **Make** — external execution; configured, execution disabled
- **n8n** — **blocked** (SSL certificate mismatch + HTTP 405)
- **Pinecone** — **disabled** (PostgreSQL FTS remains Source of Truth)
- **Yandex Direct / Metrica** — configured; write/budget disabled

See also: [h2_7_execution_foundation.md](h2_7_execution_foundation.md),
[external_execution_boundaries.md](external_execution_boundaries.md).
