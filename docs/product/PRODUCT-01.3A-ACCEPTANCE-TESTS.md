# PRODUCT-01.3A — Acceptance Tests

**Slice:** Intake & Hydration Consent Gate  
**Automated:** `tests/test_product_01_3a_biv_intake_gate.py`

---

## Backend (automated)

| # | Case | Status |
|---|------|--------|
| 1 | Empty context cannot start analysis | ✅ |
| 2 | Hydrated unconfirmed cannot start | ✅ |
| 3 | Confirmed restored context passes gate | ✅ |
| 4 | Edited context requires reconfirm | ✅ |
| 5 | Start new clears active draft only | ✅ |
| 6 | Historical BIV runs preserved | ✅ |
| 7 | Cross-tenant context hidden | ✅ |
| 8 | Stale snapshot hash rejected | ✅ |
| 9 | One-word / placeholder input rejected | ✅ |
| 10 | Explicit unknown geography accepted | ✅ |
| 11 | Explicit unknown audience + warning | ✅ |
| 12 | Confirm idempotent for same hash | ✅ |
| 13 | Reconfirm after content change | ✅ |
| 14 | API blocks unconfirmed run | ✅ |
| 15 | Reload → hydrated_unconfirmed | ✅ |

---

## Frontend (owner smoke — see dedicated protocol)

**Protocol:** [PRODUCT-01.3A-SMOKE-PROTOCOL.md](./PRODUCT-01.3A-SMOKE-PROTOCOL.md) — 10 steps, narrow scope.

| # | Case |
|---|------|
| 1–10 | As in smoke protocol |

---

## Gate

- **Automated:** ✅ 23 tests green
- **Owner smoke:** ⏳ pending
- **Full acceptance (01.3E):** blocked until 01.3B → 01.3C → 01.3D
