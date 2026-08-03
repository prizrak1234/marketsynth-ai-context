"use client";

import { useLocale } from "@/lib/i18n/locale-context";
import { LOCALE_OPTIONS } from "@/lib/i18n/config";

/** Minimal public landing footer. */
export function PublicFooter() {
  const { t, locale, setLocale } = useLocale();
  const enabledLocales = LOCALE_OPTIONS.filter((o) => o.enabled);

  return (
    <footer
      className="border-t px-4 py-8 sm:px-10"
      style={{
        borderColor: "var(--ms-border-default)",
        color: "var(--ms-text-muted)",
      }}
      data-testid="public-landing-footer"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs">{t("landing.footer.copyright")}</p>
        <div className="flex items-center gap-2">
          <span className="text-xs">{t("landing.footer.language")}</span>
          {enabledLocales.map((option) => (
            <button
              key={option.value}
              type="button"
              className="rounded px-2 py-1 text-xs font-medium transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]"
              style={{
                color:
                  locale === option.value
                    ? "var(--ms-text-primary)"
                    : "var(--ms-text-muted)",
                background:
                  locale === option.value ? "var(--ms-bg-elevated)" : "transparent",
              }}
              data-testid={`public-locale-${option.value}`}
              aria-pressed={locale === option.value}
              onClick={() => setLocale(option.value as "ru" | "en")}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </footer>
  );
}
