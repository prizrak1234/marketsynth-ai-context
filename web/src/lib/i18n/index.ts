export type { AppLocale } from "@/lib/i18n/config";
export {
  DEFAULT_LOCALE,
  LOCALE_OPTIONS,
  LOCALE_STORAGE_KEY,
  PREFS_STORAGE_KEY,
  SUPPORTED_LOCALES,
  resolveLocale,
} from "@/lib/i18n/config";
export { getTimezoneGroups } from "@/lib/i18n/timezones";
export {
  labelErrorCode,
  labelLifecycle,
  labelTaskStatus,
  labelTaskType,
  labelVerdictType,
  translate,
} from "@/lib/i18n/domain-labels";
export {
  DEFAULT_PREFS,
  formatDate,
  formatDateTime,
  formatMoneyRub,
  formatPercent,
  formatRelative,
  type WorkspaceUiPrefs,
} from "@/lib/i18n/formatters";
export { LocaleProvider, useLocale, useT } from "@/lib/i18n/locale-context";
