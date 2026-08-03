# Business Tool Abstraction

Skills reference normalized BusinessTools, never provider SDKs or secret env
names.

## Codes

- `knowledge_retrieval`
- `web_search` → XMLRiver (read-only)
- `source_fetch` → Firecrawl (read-only, single URL)
- `structured_extraction`
- `image_generation`
- `workflow_automation` (Make/n8n) — **not resolvable** in H2.7
- `advertising_platform` (Yandex Direct) — **not resolvable** in H2.7

Source candidates returned by search/fetch are never Evidence. Evidence
requires a later validation step.

Code: `app/business_tools/`.
