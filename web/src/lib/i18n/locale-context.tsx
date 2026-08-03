"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  PREFS_STORAGE_KEY,
  resolveLocale,
  type AppLocale,
} from "@/lib/i18n/config";
import { translate } from "@/lib/i18n/domain-labels";
import {
  DEFAULT_PREFS,
  type WorkspaceUiPrefs,
} from "@/lib/i18n/formatters";

type LocaleContextValue = {
  locale: AppLocale;
  setLocale: (locale: AppLocale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  prefs: WorkspaceUiPrefs;
  setPrefs: (patch: Partial<WorkspaceUiPrefs>) => void;
  persistenceNote: string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readStoredLocale(): AppLocale | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (!raw) return null;
    return resolveLocale([raw]);
  } catch {
    return null;
  }
}

function readStoredPrefs(): WorkspaceUiPrefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = window.localStorage.getItem(PREFS_STORAGE_KEY);
    if (!raw) return DEFAULT_PREFS;
    return { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<WorkspaceUiPrefs>) };
  } catch {
    return DEFAULT_PREFS;
  }
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<AppLocale>(DEFAULT_LOCALE);
  const [prefs, setPrefsState] = useState<WorkspaceUiPrefs>(DEFAULT_PREFS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = readStoredLocale();
    const browser =
      typeof navigator !== "undefined" ? navigator.language : undefined;
    setLocaleState(resolveLocale([stored, browser, DEFAULT_LOCALE]));
    setPrefsState(readStoredPrefs());
    setHydrated(true);
  }, []);

  const setLocale = useCallback((next: AppLocale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const setPrefs = useCallback((patch: Partial<WorkspaceUiPrefs>) => {
    setPrefsState((prev) => {
      const next = { ...prev, ...patch };
      try {
        window.localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) =>
      translate(locale, key, params),
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
      prefs,
      setPrefs,
      persistenceNote: hydrated
        ? "locale_local_draft"
        : "locale_pending",
    }),
    [locale, setLocale, t, prefs, setPrefs, hydrated],
  );

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return ctx;
}

export function useT() {
  return useLocale().t;
}
