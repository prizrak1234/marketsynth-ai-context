import type { AppLocale } from "@/lib/i18n/config";

export type WorkspaceUiPrefs = {
  timezone: string;
  dateFormat: "locale" | "iso";
  timeFormat: "24h" | "12h";
  density: "comfortable" | "compact";
  defaultLanding: "/workspace" | "/workspace/projects" | "/workspace/tasks";
  notifyEmail: boolean;
  notifyProject: boolean;
  notifyVerdict: boolean;
  notifySecurity: boolean;
};

export const DEFAULT_PREFS: WorkspaceUiPrefs = {
  timezone: "Europe/Moscow",
  dateFormat: "locale",
  timeFormat: "24h",
  density: "comfortable",
  defaultLanding: "/workspace",
  notifyEmail: true,
  notifyProject: true,
  notifyVerdict: true,
  notifySecurity: true,
};

export function formatDate(
  locale: AppLocale,
  value: string | Date | null | undefined,
  prefs?: Pick<WorkspaceUiPrefs, "dateFormat" | "timezone">,
): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  if (prefs?.dateFormat === "iso") {
    return date.toISOString().slice(0, 10);
  }
  return new Intl.DateTimeFormat(locale === "ru" ? "ru-RU" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: prefs?.timezone || undefined,
  }).format(date);
}

export function formatDateTime(
  locale: AppLocale,
  value: string | Date | null | undefined,
  prefs?: WorkspaceUiPrefs,
): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(locale === "ru" ? "ru-RU" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: prefs?.timeFormat === "12h",
    timeZone: prefs?.timezone || undefined,
  }).format(date);
}

export function formatRelative(
  locale: AppLocale,
  value: string | Date | null | undefined,
): string {
  if (!value) return "—";
  const date = typeof value === "string" ? new Date(value) : value;
  const diffSec = Math.round((date.getTime() - Date.now()) / 1000);
  const rtf = new Intl.RelativeTimeFormat(locale === "ru" ? "ru" : "en", {
    numeric: "auto",
  });
  const abs = Math.abs(diffSec);
  if (abs < 60) return rtf.format(diffSec, "second");
  if (abs < 3600) return rtf.format(Math.round(diffSec / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diffSec / 3600), "hour");
  return rtf.format(Math.round(diffSec / 86400), "day");
}

export function formatPercent(locale: AppLocale, value: number): string {
  return new Intl.NumberFormat(locale === "ru" ? "ru-RU" : "en-GB", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value / 100);
}

export function formatMoneyRub(locale: AppLocale, value: number): string {
  return new Intl.NumberFormat(locale === "ru" ? "ru-RU" : "en-GB", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(value);
}
