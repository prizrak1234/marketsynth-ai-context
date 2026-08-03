# Marketsynth Brand Policy

**Product:** Marketsynth  
**Status:** ACTIVE (Phase V2.1)  
**Date:** 2026-07-13  
**Authority:** Product branding foundation; does not override Marketsynth Architecture SoT  

---

## 1. Official name

| Form | Usage |
|---|---|
| **Marketsynth** | Official commercial / release / UI / metadata name |
| **MARKETSYNTH** | Logo wordmark and brand headlines only |
| **BotFazer** | Former internal working name — legacy identifiers only |

Rules:

- New user-facing UI and messages use **Marketsynth** only.
- Metadata, titles, onboarding, and public docs use **Marketsynth**.
- Do **not** add new user-facing BotFazer strings.
- Do **not** globally rename packages, imports, tables, migrations, env vars, API routes, or persisted values without a dedicated migration phase.

---

## 2. Logo

Master asset (immutable reference):

```text
web/public/brand/marketsynth-logo-master.png
```

Contains: MS monogram, MARKETSYNTH wordmark, dark field, gold + cool blue accents.

Forbidden without a separate task: redraw, recolor, stretch, crop, effects, AI-generated substitutes, random UI icons as logo.

### Missing derivative assets (not generated in V2.1)

- `marketsynth-logo-horizontal`
- `marketsynth-symbol`
- `marketsynth-wordmark`
- `marketsynth-logo-dark`
- `marketsynth-logo-light`
- `marketsynth-favicon`
- `marketsynth-og-image`

Until `marketsynth-symbol` / favicon exist, chrome UI uses **text** `PRODUCT_BRAND.displayName`. Do not crop the master asset into a favicon.

Central config: `web/src/lib/brand/product-brand.ts` → `PRODUCT_BRAND`.

---

## 3. Palette and tokens

Core HEX values and semantic CSS variables live in:

```text
web/src/styles/brand-tokens.css
```

TypeScript token path mirror:

```text
web/src/lib/brand/tokens.ts
```

Do not hardcode brand HEX in components. Use semantic tokens (`--ms-*` / `--brand-*`).

### Color roles

| Color | Use |
|---|---|
| Gold | Brand accents, premium CTA, selected premium states, identity — **sparingly** |
| Blue | Primary actions, focus, active, AI/analytics, links, info |
| Status/risk/verdict/evidence/approval/execution | Dedicated semantic tokens — **not** gold/blue for everything |

---

## 4. Visual direction

Marketsynth is a professional AI marketing platform (validation, risk, strategy, execution) — not a chatbot toy, messenger clone, crypto skin, or neon-AI demo.

Approved first-screen copy is frozen in `PRODUCT_BRAND.hero` — do not rewrite without permission.

---

## 5. Local working mode (Phase V2.1 note)

Brand and Architecture V2.1 work may be performed **locally only**. Remote git publish is a separate explicit command after review.
