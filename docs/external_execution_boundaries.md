# External Execution Boundaries

## Hard rules (H2.7)

- Make: configured only; no automatic scenario runs
- n8n: **blocked** (SSL mismatch + API method mismatch). Do not bypass TLS.
- Yandex Direct: write/budget actions disabled
- Pinecone: disabled; PostgreSQL remains Source of Truth
- Publication: never triggered by content draft execution
- Campaign / budget: never created by specialist draft paths

## Approval boundary (future)

```
draft → owner approval → execution package → Make / n8n / advertising write
```

Never:

```
user message → n8n / Make / Direct write
```
