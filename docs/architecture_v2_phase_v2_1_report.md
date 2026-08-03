# Architecture v2.0 — Phase V2.1 Report

**Phase:** V2.1 — Architecture compatibility and contracts + Brand foundation  
**Date:** 2026-07-13  
**Implementation tree:** local BotFazer package checkout @ baseline `928a357`  
**Remote git operations:** **none** (no fetch/pull/push/clone)  
**Runtime behavior:** **unchanged** (additive contracts + brand config only)

Related:

- `docs/architecture_v2_compatibility_audit.md` (SoT repo / prior audit)
- `docs/architecture_v2_migration_plan.md`
- `docs/architecture_v2_regression_policy.md`
- `docs/marketsynth_brand_policy.md`
- `docs/marketsynth_brand_migration_audit.md`
- Marketsynth SoT: `PROJECT_CONSTITUTION.md`, `CORE_CONTRACT_DEFINITIONS.md`, runtime models

---

## 1. Scope completed

### Architecture

- Additive StrEnums / models in `app/schemas/contracts.py` for Verification, Provider, Tool layers, Reasoning artifacts, Verdict (incl. `INSUFFICIENT_DATA`), Evidence/Approval/Execution semantic states, Q0–Q6 gates
- `ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS` inventory (Marketsynth concept → legacy artifact)
- Characterization tests: `tests/test_phase_architecture_v2_1_contracts.py`
- **No** tables, Alembic migrations, endpoint changes, enum value mutations of existing enums, providers, or MCP

### Brand

- Official name **Marketsynth** in UI metadata / sidebar / scenario copy
- Master logo stored unmodified at `web/public/brand/marketsynth-logo-master.png`
- `PRODUCT_BRAND` + approved hero copy at `web/src/lib/brand/product-brand.ts`
- Design token foundation at `web/src/styles/brand-tokens.css` (+ TS mirror)
- Missing derivative assets listed; not generated
- Brand policy + migration audit docs

---

## 2. Explicitly out of scope (not started)

- Phase V2.2 Verified Execution wiring  
- Real providers / MCP  
- Full UI recolor / redesign  
- Global BotFazer → Marketsynth identifier rename  
- Alembic / DB drift repair  
- AI.84 SyntaxError fix  
- Repo-wide ruff cleanup  

---

## 3. Checks (local)

| Check | Result |
|---|---|
| V2.1 contract tests | See verification run in session |
| `ruff check` on touched Python | Targeted only |
| Frontend lint on touched files | Targeted |
| User-facing BotFazer in `web/src` | Should be none except `formerWorkingName` |
| Remote git | Not used |

Pre-existing (unchanged): AI.84 collection error; ruff 433 repo-wide; alembic DB stamp drift; eslint parse in `e2e-demo-flow-checklist.tsx`.

---

## 4. Recommendation

After local review of this phase, next approved step is **Phase V2.2 — Verified Execution contracts** (still behind feature flag; Telegram wrap first). Do not start V2.2 without explicit permission.

---

```text
Phase V2.1 completed locally.
Marketsynth branding foundation established.
No remote repository operations performed.
No runtime behavior changed.
Ready for review before Phase V2.2.
```
