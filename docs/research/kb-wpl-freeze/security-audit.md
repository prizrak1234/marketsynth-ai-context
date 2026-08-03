# Security audit

Scanned: `app/knowledge/{workflow_catalog,workflow_patterns,n8n_engineering,knowledge_linking,presentation_architecture,capability_model,discovery}`

| Check | Result |
|-------|--------|
| Network imports (requests/httpx/socket/mcp) | None |
| Subprocess execution | None |
| Raw secrets in program bundle | None |
| Absolute local paths in manifest | None |
| Raw workflow node bodies in catalog | None |
| Raw n8n JSON in pattern files | None |
| Discovery rejects credential-like input | ✅ |

Verdict: no security blockers.
