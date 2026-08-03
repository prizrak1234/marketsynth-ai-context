# Higgsfield Sandbox Freeze Audit

**Work package:** CONN-HF-01.1L — B13  
**Current status:** `sandbox_verification_required`  
**Target status (after all gates):** `sandbox_verified`

---

## Freeze criteria checklist

| # | Criterion | Factual |
|---|-----------|---------|
| 1 | Authentication mechanism confirmed | ☐ |
| 2 | Protocol version confirmed | ☐ |
| 3 | Real tools captured | ☐ |
| 4 | Real image schema captured | ☐ |
| 5 | Schema hash verified | ☐ |
| 6 | Canonical mapping manually approved | ☐ |
| 7 | One image call executed | ☐ |
| 8 | Job/status model documented | ☐ |
| 9 | Result handling documented | ☐ |
| 10 | Billing visibility documented | ☐ |
| 11 | Evidence descriptor created | ☐ |
| 12 | Tokens absent from artifacts/logs | ☐ |
| 13 | Video disabled | ✓ (code) |
| 14 | Customer live path blocked | ✓ (code) |

---

## Required flags after freeze

| Flag | Required value |
|------|----------------|
| production_eligible | false |
| customer_live_generation | false |
| tenant_enabled | false |
| video_enabled | false |

**Forbidden status values:** `production_ready`, `active`, `globally_enabled`

---

## Manifest location

`packages/connectors/higgsfield/sandbox/freeze_manifest.json`

---

## Next connector slice (not this task)

**CONN-HF-01.2** — Tenant Credential Binding + Production Image Render
