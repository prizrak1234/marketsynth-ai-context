/** Marketsynth workspace i18n configuration. */

export const SUPPORTED_LOCALES = ["ru", "en"] as const;
export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

/** Planned UI locales — enabled only when listed in SUPPORTED_LOCALES. */
export const LOCALE_OPTIONS: ReadonlyArray<{
  value: string;
  label: string;
  enabled: boolean;
}> = [
  { value: "ru", label: "Русский", enabled: true },
  { value: "en", label: "English", enabled: true },
  { value: "tr", label: "Türkçe", enabled: false },
  { value: "de", label: "Deutsch", enabled: false },
  { value: "es", label: "Español", enabled: false },
  { value: "fr", label: "Français", enabled: false },
  { value: "ar", label: "العربية", enabled: false },
];

export const DEFAULT_LOCALE: AppLocale = "ru";

export const LOCALE_STORAGE_KEY = "marketsynth.ui.locale.v1";
export const PREFS_STORAGE_KEY = "marketsynth.ui.prefs.v1";

export function isAppLocale(value: string | null | undefined): value is AppLocale {
  return value === "ru" || value === "en";
}

export function resolveLocale(candidates: Array<string | null | undefined>): AppLocale {
  for (const c of candidates) {
    if (!c) continue;
    const short = c.toLowerCase().slice(0, 2);
    if (isAppLocale(short)) return short;
  }
  return DEFAULT_LOCALE;
}
