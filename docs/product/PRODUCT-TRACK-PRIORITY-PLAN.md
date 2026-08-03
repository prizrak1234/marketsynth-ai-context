# Product Track Priority Plan

**Superseded as execution queue by:** [PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md)

---

## Decision rule

> One finished commercial route beats twenty infrastructure slices without customer outcome.

**Stop horizontal expansion.** Ship the golden path end-to-end.

---

## Active program

| Priority | Program | Status |
|----------|---------|--------|
| **P0** | [PRODUCT-FINISH-01](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md) | **active** |
| Step A | 01.3B.2A research value | `waiting_for_owner_validation` |
| Step B | [PRODUCT-QA-01](./PRODUCT-QA-01-COMMERCIAL-ACCEPTANCE-HARNESS.md) | blocked until A PASS |
| Steps C–E | 01.3C → 01.3D → 01.3E | blocked |
| Step F | Freeze PRODUCT-01 | blocked |
| Step G | [PRODUCT-02 Telegram](./PRODUCT-02-TELEGRAM-PUBLICATION-GOLDEN-PATH.md) | blocked |
| Step J | [LEGACY Visual Golden Path](./PRODUCT-03-VISUAL-ASSET-GOLDEN-PATH.md) (historical PRODUCT-03 ID; not Strategy Architecture) | frozen |

---

## Frozen (until commercial MVP v1)

- KB-WPL-02, Knowledge Core persistence, vector search
- Skill marketplace, new professions, generic assistant expansion
- Higgsfield / video (except LEGACY Visual Golden Path / FINISH Step J after Telegram)
- Multi-channel publish, site builder, presentations
- New Home / parallel workflows outside CWF golden path

---

## Legacy corrective slices (01.3A–01.3B.2)

Historical only — do **not** open new micro-slices. Roll remaining work into **FINISH-01 steps A–E**.

| Slice | Note |
|-------|------|
| 01.3A | accepted (intake-only) |
| 01.3B.1 | presentation partial |
| 01.3B.2 | coverage contract implemented |
| **01.3B.2A** | **current gate** — research commercial value |

---

## Owner gate

No step advances without **`owner_accepted`** on browser smoke for that step.

Cursor terminal status: **`waiting_for_owner_validation`** until owner verdict.
