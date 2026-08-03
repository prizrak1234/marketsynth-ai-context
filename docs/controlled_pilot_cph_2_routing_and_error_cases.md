# CPH.2 — Routing and error cases

Specs: `web/e2e/routing-guards.spec.ts`, `web/e2e/hybrid-smoke.spec.ts`

## Covered in browser

| Case | Expectation |
|------|-------------|
| Strategy with missing/invalid project | Honest empty/blocked — no fake Strategy |
| Implementation without plan | Honest shell + no mock specialist progress |
| Landing in backend mode | CTA works; no “Integration: mock” claim from env |
| Hybrid smoke | Mode can be hybrid; no silent MarketingPlan auto-approve |

## Backend remains authoritative

Direct URL entry to Strategy/Implementation cannot bypass API ownership or eligibility. Route UI is not a security control.

## Error UX (observed / deferred)

| Condition | UI behaviour |
|-----------|----------------|
| Validation on intake | Per-field errors + banner |
| Brief not submitted | Investigation create fails with action hint |
| Handoff without checkbox | `explicit_confirmation_required` |
| Backend unavailable | Integration adapters surface error + hint (no mock fill) |

Full matrix of stale fingerprint / unsupported role remains covered primarily by backend P1.2/P1.3 tests; CPH.2 focuses on browser visibility of honesty.
