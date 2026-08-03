"use client";

import { useLocale } from "@/lib/i18n";

const USP_KEYS = ["viability", "routing", "evidence"] as const;

/** Differentiated home value props — not generic agency principles. */
export function HomeUspBlock() {
  const { t } = useLocale();

  return (
    <section className="space-y-5" data-testid="home-usp">
      <p
        className="max-w-3xl text-base font-medium leading-relaxed sm:text-lg"
        style={{ color: "var(--ms-text-primary)" }}
        data-testid="home-economic-value"
      >
        {t("home.usp.economicValue")}
      </p>

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {USP_KEYS.map((key) => (
          <li
            key={key}
            className="rounded-xl border px-4 py-5"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-surface)",
            }}
            data-testid={`home-usp-${key}`}
          >
            <h3
              className="text-base font-semibold leading-snug"
              style={{ color: "var(--ms-text-primary)" }}
            >
              {t(`home.usp.${key}.title`)}
            </h3>
            <p
              className="mt-2 text-sm leading-relaxed"
              style={{ color: "var(--ms-text-secondary)" }}
            >
              {t(`home.usp.${key}.body`)}
            </p>
          </li>
        ))}
      </ul>

      <p
        className="rounded-lg border px-4 py-3 text-sm leading-relaxed sm:text-[15px]"
        style={{
          borderColor: "color-mix(in srgb, var(--ms-brand-secondary) 35%, transparent)",
          background:
            "color-mix(in srgb, var(--ms-brand-secondary) 8%, var(--ms-bg-elevated))",
          color: "var(--ms-text-primary)",
        }}
        data-testid="home-usp-control"
      >
        {t("home.usp.controlLine")}
      </p>
    </section>
  );
}
