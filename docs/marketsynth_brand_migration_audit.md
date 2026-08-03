# Marketsynth Brand Migration Audit

**Date:** 2026-07-13  
**Phase:** V2.1  
**Baseline commit:** `928a357`  
**Scope:** Name + brand asset inventory (no global rename)

Categories: `user-facing` | `internal legacy` | `historical` | `uncertain`

---

## Inventory

| Location | Current value | Category | Change now | Risk | Recommended action |
|---|---|---|---|---|---|
| `web/src/app/layout.tsx` metadata title/description | Was `BotFazer — Internal Operations` | user-facing | **Yes → Marketsynth via PRODUCT_BRAND** | Low | Done in V2.1 |
| `web/src/components/layout/app-sidebar.tsx` brand label | Was `BotFazer` | user-facing | **Yes → PRODUCT_BRAND.displayName** | Low | Done in V2.1 |
| `web/src/components/agent-chat/marketing-scenarios-picker.tsx` | “BotFazer assembles…” | user-facing | **Yes → Marketsynth** | Low | Done in V2.1 |
| `web/src/lib/brand/product-brand.ts` `formerWorkingName` | `BotFazer` | historical | Keep | None | Documents former name intentionally |
| `web/src/lib/api/config.ts` | `NEXT_PUBLIC_BOTFAZER_*` env keys | internal legacy | **No** | High if renamed | Leave; migrate later with dual-read |
| `web/src/components/data/config-missing.tsx` | Shows `NEXT_PUBLIC_BOTFAZER_*` examples | internal legacy | **No** | Medium | Leave until env rename phase |
| `web/README.md` title | `BotFazer Web` | historical / developer | Soft update | Low | Note Marketsynth + legacy package |
| `README.md` | `# BotFazer` | historical | Soft note | Low | Add Marketsynth official name note |
| `AGENTS.md` | BotFazer assistant instructions | historical / internal | Soft note | Low | Add official product name preamble |
| `pyproject.toml` `name = "botfazer"` | Python package name | internal legacy | **No** | High | Controlled package rename later |
| `app/schemas/contracts.py` module docstring | Referenced BotFazer | historical | Updated to Marketsynth + legacy note | Low | Done in V2.1 |
| DB / Alembic / table names | `botfazer` not generally in table names; package paths | internal legacy | **No** | High | Out of scope |
| API routes `/…` | No product-name path prefix required | internal legacy | **No** | — | Keep |
| Phase docs under `docs/phase_ai_*` | BotFazer phase language | historical | **No** | Low | Keep; historical working name |
| Marketsynth SoT repo docs | Already Marketsynth | user-facing / SoT | N/A | — | Authoritative naming |
| Logo master asset | Missing before V2.1 | user-facing | **Added** `web/public/brand/marketsynth-logo-master.png` | Low | Done; do not edit pixels |
| Favicon / OG / symbol | Missing | user-facing | **No** (missing inventory) | Low | Provide dedicated assets later |
| Design tokens | Scattered shadcn neutrals | uncertain | **Foundation added** | Low | Gradual mapping in later UI phases — no mass recolor in V2.1 |

---

## Summary

| Category | Count (rows above) | V2.1 action |
|---|---:|---|
| user-facing | 3 replaced + logo/tokens | Replaced / added |
| internal legacy | env keys, package name, config hints | Preserved |
| historical | README/AGENTS/phase docs | Noted / light preamble |
| uncertain | theme migration depth | Token foundation only |

---

## Verification checklist

- [x] No new user-facing BotFazer strings introduced (except intentional `formerWorkingName`)
- [x] Master logo SHA256 preserved on copy
- [x] `PRODUCT_BRAND.assets.master` points to `/brand/marketsynth-logo-master.png`
- [x] Brand HEX centralized in `brand-tokens.css`
- [x] Env vars `NEXT_PUBLIC_BOTFAZER_*` unchanged
