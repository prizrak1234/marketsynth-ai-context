# Home hero — brand logo anchor

## Sizing

| Viewport | Height |
|----------|--------|
| Desktop | `clamp(180px, 16vw, 230px)` |
| Mobile | `clamp(150px, 28vw, 190px)` |

Aspect ratio preserved from master `1024×579`. Master file is never modified
(`SHA256 233FC4CCC844A700D4944FC6FA30BBA3017C39A6B5343D4122FD18DEA568DF37`).

## Layout

- Desktop grid ≈ **36% / 64%**, `items-center`, gap `clamp(2.5rem, 5vw, 4.5rem)`
- Mobile: sidebar collapses to top bar + drawer; content full-width so logo can hit 150–190px
- Single-column hero, logo centered above copy
- No “AI MARKETING AGENCY” caption under the mark
- Greeting capped ≈ **2–2.25 rem** so the mark remains equal visual weight

## Entrance

- Once per tab session (`sessionStorage` key `marketsynth.home.logo-entrance.v1`)
- Scale 0.96 → 1, soft fade, brief secondary drop-shadow, left→right gleam overlay
- Duration ≈ **1s**, `animation-iteration-count: 1`, no loop
- `prefers-reduced-motion: reduce` → no motion / gleam; logo shown immediately

## Roles

| Surface | Component | Size |
|---------|-----------|------|
| Home hero | `BrandLogoHero` | 180–230 px height |
| Sidebar | `BrandLogoMark` / symbol | ~28–30 px |
| Favicon | derived assets | technical |
