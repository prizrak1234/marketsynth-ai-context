import type { AppLocale } from "@/lib/i18n/config";
import { lookupTranslation, type TranslationTree } from "@/lib/i18n/lookup";
import { en } from "@/lib/i18n/translations/en";
import { ru } from "@/lib/i18n/translations/ru";

const DICTS: Record<AppLocale, TranslationTree> = { ru, en };

export function getDictionary(locale: AppLocale): TranslationTree {
  return DICTS[locale] ?? DICTS.ru;
}

export function translate(
  locale: AppLocale,
  key: string,
  params?: Record<string, string | number>,
): string {
  const primary = lookupTranslation(getDictionary(locale), key, params);
  if (primary !== key) return primary;
  if (locale !== "en") {
    const fallback = lookupTranslation(getDictionary("en"), key, params);
    if (fallback !== key) return fallback;
  }
  return key;
}

/** Domain helpers — always go through translation keys, never raw enums. */
export function labelTaskStatus(locale: AppLocale, status: string): string {
  return translate(locale, `task.status.${status}`);
}

export function labelTaskType(locale: AppLocale, type: string): string {
  return translate(locale, `task.type.${type}`);
}

export function labelVerdictType(locale: AppLocale, type: string): string {
  const normalized = type.toLowerCase();
  return translate(locale, `verdicts.type.${normalized}`);
}

export function labelLifecycle(locale: AppLocale, status: string): string {
  return translate(locale, `lifecycle.${status}`);
}

export function labelErrorCode(locale: AppLocale, code: string): string | null {
  const key = `errors.${code}`;
  const text = translate(locale, key);
  return text === key ? null : text;
}
