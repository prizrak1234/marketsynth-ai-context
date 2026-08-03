/**
 * Central Marketsynth product brand configuration.
 * Do not scatter product name or logo paths across components — import from here.
 */
export const PRODUCT_BRAND = {
  name: "Marketsynth",
  displayName: "Marketsynth",
  logoDisplayName: "MARKETSYNTH",
  formerWorkingName: "BotFazer",
  positioning:
    "AI-маркетинговое агентство, которое сначала проверяет жизнеспособность идеи, оценивает риски и только потом строит стратегию развития.",
  assets: {
    /** Master/reference asset (full mark on dark). Not a universal UI glyph. Do not edit. */
    master: "/brand/marketsynth-logo-master.png",
    masterSha256:
      "233FC4CCC844A700D4944FC6FA30BBA3017C39A6B5343D4122FD18DEA568DF37",
    /** Full mark for Home hero — master file, bounded responsively. */
    horizontal: "/brand/marketsynth-logo-master.png",
    /** Compact MS emblem derived from master (sidebar / headers). */
    symbol: "/brand/marketsynth-symbol.png",
    symbolDark: "/brand/marketsynth-symbol-dark.png",
    wordmark: null,
    light: null,
    dark: "/brand/marketsynth-logo-master.png",
    favicon: "/brand/marketsynth-favicon.ico",
    favicon32: "/brand/marketsynth-favicon-32.png",
    appleTouchIcon: "/brand/marketsynth-apple-touch-icon.png",
    openGraph: null,
  },
  /** Approved first-screen copy — do not rewrite without explicit permission. */
  hero: {
    headline: "Прежде чем потратить ваши деньги, мы поможем их сохранить.",
    subheadline:
      "Marketsynth — AI-маркетинговое агентство, которое сначала проверяет жизнеспособность идеи, оценивает риски и только потом строит стратегию развития.",
    benefits: [
      "Проверим, стоит ли вообще запускать проект.",
      "Найдём слабые места до того, как они станут убытками.",
      "Если идея обречена — честно скажем об этом и объясним почему.",
    ] as const,
    primaryCta: "Проверить мою идею",
  },
} as const;

export type ProductBrand = typeof PRODUCT_BRAND;

/** Remaining planned derivatives (not required for authenticated IA). */
export const MISSING_BRAND_ASSETS = [
  "marketsynth-logo-horizontal-light",
  "marketsynth-wordmark-standalone",
  "marketsynth-og-image",
] as const;
