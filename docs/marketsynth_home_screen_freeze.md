# Marketsynth Home Screen — FREEZE

**Status:** FROZEN / APPROVED  
**Date:** 2026-07-13  
**Authority:** Explicit user approval — do not change until the user says so

---

## Approved composition

Local URL (dev): `http://localhost:3000/`

First screen includes:

1. Marketsynth master logo (`/brand/marketsynth-logo-master.png`) **above** the product name  
2. Product name: **Marketsynth**  
3. Frozen hero copy from `PRODUCT_BRAND.hero` (headline, subheadline, benefits, CTA «Проверить мою идею»)  
4. Brand canvas / navy surfaces / gold + blue accents aligned with the logo  

Supporting chrome for the home experience:

- `AppShell` brand canvas background  
- Sidebar brand styling  

---

## Locked files (visual / home composition)

Do **not** edit without a new explicit user command:

- `web/src/components/brand/marketsynth-home-hero.tsx`
- `web/src/components/views/dashboard-view.tsx` (hero placement / home structure)
- `web/src/components/layout/app-shell.tsx` (brand canvas used by home)
- `web/src/components/layout/app-sidebar.tsx` (brand chrome as approved with home)
- `web/src/styles/brand-tokens.css` (palette driving the home look)
- `web/public/brand/marketsynth-logo-master.png` (master asset — never edit pixels)
- `web/src/lib/brand/product-brand.ts` (`hero` copy and `assets.master`)

---

## Allowed without unfreezing home

- Backend / Architecture V2 phases that do not touch the files above  
- Fixes on other routes (e.g. `/agents/chat`) that do not alter home visuals  
- Docs unrelated to home layout  

---

## Rule

```text
Home screen is approved.
Do not redesign, recolor, rewrite copy, move the logo, or change CTA
until the user explicitly unfreezes this screen.
```
