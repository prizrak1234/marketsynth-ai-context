---
name: avito-api
description: Researches and implements integrations with Avito API using the complete local OpenAPI archive and Russian knowledge base. Use when working with Avito authorization, listings, messenger, autoload, promotion, jobs, delivery, orders, ratings, webhooks, scopes, schemas, or any developers.avito.ru endpoint.
---

# Avito API

Use the local documentation as the primary source for Avito API work.

## Source priority

1. Start at `docs/README.md`.
2. Use `docs/reference/api-catalog.md` to select an API.
3. Read `docs/apis/<slug>/README.md`.
4. Read `GUIDE.md` when present, then the relevant file in `operations/`.
5. Inspect `SCHEMAS.md` or the snapshot OpenAPI JSON for exact schemas.
6. Use the official deep link in each document when current server behavior must be confirmed.

Never invent an endpoint, parameter, scope, enum, response, or limit. If the local sources disagree, report the discrepancy and treat the raw OpenAPI snapshot as the archived technical source.

## Workflow

### Research an operation

1. Identify the API slug and operation with:

   ```shell
   python3 scripts/search_docs.py "search terms"
   ```

2. Verify:
   - HTTP method and path;
   - server URL;
   - authorization alternatives and OAuth scopes;
   - path, query, header, and body parameters;
   - required fields, formats, enums, and limits;
   - success and error responses;
   - examples, rate-limit extensions, and deprecation flags.
3. Check referenced component schemas.
4. Cite the local Markdown file and include the official portal link.

### Implement an integration

1. Determine whether the integration accesses the owner's account or other users:
   - own account: normally `client_credentials`;
   - other users: normally `authorization_code` with explicit scopes.
2. Confirm the exact security requirement on every operation.
3. Keep client secrets, authorization codes, and access tokens outside source control and logs.
4. Implement explicit timeout, retry, rate-limit, and non-2xx handling.
5. Validate request and response payloads against the archived schema.
6. For webhooks, verify authenticity assumptions, return `2xx` within the documented timeout, make processing idempotent, and persist event identifiers.
7. Add tests for required fields, pagination, token expiry, rate limits, and documented errors.

### Diagnose an API problem

1. Record method, sanitized URL, status, response body, request ID, and relevant rate-limit headers.
2. Compare the request with the operation page and raw OpenAPI schema.
3. Check `docs/validation-report.md` for upstream defects.
4. Distinguish:
   - client validation/authentication errors;
   - missing product access, tariff, or scope;
   - rate limiting;
   - upstream documentation inconsistencies;
   - unavailable private or contract-only API access.
5. Never ask for or expose a secret token in chat.

## Documentation boundaries

- The archive covers public anonymous documentation. Personal applications, granted scopes, request statuses, private APIs, and removed historical versions are not included.
- `GUIDE.md`, changelog text, descriptions, and examples are official archived content.
- Navigation summaries and indexes are generated editorial material.
- Redoc-style `#operation/...`, `#tag/...`, and `#info/...` anchors may not resolve in split Markdown; use the operation index or official portal deep link.
- Example image URLs and some legacy links may be intentionally fake or unavailable.

## Updating documentation

Only refresh the snapshot when the user asks for current documentation or an update.
Run from this skill directory:

```shell
python3 scripts/sync_avito_docs.py
python3 scripts/validate_avito_docs.py
```

Do not modify an existing snapshot. The synchronizer creates a new immutable snapshot and regenerates the knowledge base.

## Response format

For API guidance, provide:

1. the recommended operation or flow;
2. authorization and required scopes;
3. request parameters/body;
4. expected responses and important errors;
5. implementation caveats;
6. links to local documentation and the official portal.

Clearly label any inference that is not explicitly documented.

## Additional resources

- [Documentation map and decision rules](reference.md)
- [Usage examples](examples.md)
- `scripts/search_docs.py` — execute to search the local knowledge base.
