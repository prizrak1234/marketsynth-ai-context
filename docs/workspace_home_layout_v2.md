# Home layout v2

- Content max-width ≈ **1360px**
- Hero: **36% / 64%** columns desktop — logo left (brand anchor), greeting + offer + support right
- Logo height: desktop `clamp(180px, 16vw, 230px)`; mobile `clamp(150px, 28vw, 190px)`; no caption
- One-shot entrance (~1s: fade, scale 0.96→1, edge glow, gleam) once per tab session; then static
- `prefers-reduced-motion` disables gleam / motion
- Support = approved positioning line (agency + viability-first)
- Greeting ~2–2.25rem so mark keeps equal weight with the offer
- Below hero: USP → question → conversation → input → scenarios
- Details: [workspace_home_logo_anchor.md](workspace_home_logo_anchor.md), [workspace_home_usp.md](workspace_home_usp.md)
