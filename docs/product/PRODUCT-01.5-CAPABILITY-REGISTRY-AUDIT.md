# PRODUCT-01.5 — Capability Registry Pre-Implementation Audit

**Task:** PRODUCT-01.5-COMMERCIAL-CAPABILITY-REGISTRY-01  
**Date:** 2026-08-01  
**Owner decision required:** NO (IA/Journey Map aligned; no contradictory code path chosen unilaterally)

---

## 1. Sources of truth (before)

| Source | Role |
|--------|------|
| `docs/INFORMATION_ARCHITECTURE.md` | Topology, screen registry, URL contract |
| `docs/COMMERCIAL_USER_JOURNEY_MAP.md` | Journey stages J1–J11 |
| `docs/DESIGN.md` | Visual primitives |
| `web/src/lib/routes/commercial-surface.ts` | Public nav + legacy redirects |
| `web/src/lib/home/user-intent-catalog.ts` | Home direction cards (dev mode) |
| `web/src/lib/home/developer-mode.ts` | Internal surface boundary |
| `web/src/components/workspace/workspace-nav.tsx` | Hardcoded dev nav extension |

## 2. Duplications found

- Public nav items duplicated in `PUBLIC_WORKSPACE_NAV` + `DEVELOPER_NAV_ITEMS` in `workspace-nav.tsx`
- Legacy redirects in `LEGACY_COMMERCIAL_REDIRECTS` separate from capability states
- Home intent `status: partial|planned` independent of IA reserved slots
- Frozen nav hrefs in `FROZEN_PUBLIC_NAV_HREFS` parallel to internal route list

## 3. Contradictions

- IA §2.1 uses `PLACEHOLDER`; implementation task uses `reserved/planned` — mapped without IA change (operational availability vs surface class)
- `user-intent-catalog` exposes partial/planned cards in developer Home; commercial Home already uses `CanonicalCommercialEntryPanel` (RUNTIME-01E) — no production contradiction

## 4. Hardcoded capability states

- `USER_INTENTS[].status` (`supported|partial|planned`)
- `FROZEN_PUBLIC_NAV_HREFS`, `DEVELOPER_NAV_ITEMS`
- `LegacyCommercialGuard` per-route
- Feature freeze via `canBypassCommercialSurfaceFreeze()`

## 5. Proposed minimal architecture

```
web/src/lib/product-capabilities/
  contracts.ts    — capability types
  registry.ts     — canonical IA tree + availability
  selectors.ts    — nav/home/route resolution
  validation.ts   — invariants + activation contract
  registry.test.ts
```

`commercial-routes.ts` — route constants only (server-safe).  
`commercial-surface.ts` — derives nav/redirects from registry.

## 6. Scope

- Executable registry for all IA modules (available / internal / planned / reserved)
- Wire workspace nav, home intent filter (dev), legacy redirect resolution
- Activation validation + unit/E2E tests
- Preview credential cleanup

## 7. Out of scope

Research runs, Evidence Hardening, Landing/Settings slices, new modules, backend RBAC, feature-flag platform

## 8. Expected files

See implementation: `web/src/lib/product-capabilities/*`, `commercial-routes.ts`, nav/intent integration, `e2e/capability-registry-navigation.spec.ts`, `scripts/delete_preview_account.py`

## 9. Migration impact

- `PUBLIC_WORKSPACE_NAV` now derived from registry (same 3 public items)
- `isPublicWorkspaceNavVisible` requires non-production env for internal nav (stricter than before)
- No new public routes or sidebar items

## 10. Tests

- 15 registry unit tests
- 10 navigation E2E scenarios
- Existing commercial-surface + Slice E regressions

## 11. Owner decision

**NO** — proceed with registry as specified.
