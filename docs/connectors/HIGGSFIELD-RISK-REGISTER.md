# Higgsfield Risk Register

**Phase:** CONN-HF-01.1

| ID | Risk | Severity | Mitigation | Status |
|----|------|----------|------------|--------|
| R-HF-01 | Dry-run policy bypass enabled paid path without gates | Critical | Plan-only dry_run path; bypass removed from `policies.py` | **Mitigated** |
| R-HF-02 | Guessed MCP tool names used as canonical contract | High | Canonical ops + snapshot mapping only | **Mitigated** |
| R-HF-03 | Assumed Bearer OAuth for backend | High | Auth findings doc; handshake required | Open |
| R-HF-04 | Customer live calls before verification | High | `409 connector_not_production_ready` | **Mitigated** |
| R-HF-05 | Video render cost/complexity | High | `HIGGSFIELD_VIDEO_RENDER_ENABLED=false` | **Mitigated** |
| R-HF-06 | Schema drift at runtime | Medium | Hash verify before `tools/call` | **Mitigated** |
| R-HF-07 | Signed URL secrets in logs | Medium | URL query redaction | **Mitigated** |
| R-HF-08 | Unknown billing cost auto-charge | Medium | `accept_unknown_cost` gate | **Mitigated** |
| R-HF-09 | Token persistence | Critical | No DB/repo/log storage | **Mitigated** |
| R-HF-10 | CWF premature integration | Medium | No Launch Pack / publish wiring | **Mitigated** |

## Open questions

1. Actual MCP tool names and input schemas from `tools/list`
2. Auth mechanism for Marketsynth backend (Bearer vs OAuth challenge vs session)
3. Async job model and terminal statuses from provider
4. Whether separate download tool exists or results are inline/signed URL
5. Cost metadata availability before generation
