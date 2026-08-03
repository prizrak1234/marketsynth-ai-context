"use client";

import type { RecentVerdict, VerdictKindUi } from "@/lib/workspace/types";
import { labelVerdictType, useLocale } from "@/lib/i18n";

const VERDICT_STYLE: Record<
  VerdictKindUi,
  { color: string; bg: string }
> = {
  GO: {
    color: "var(--ms-verdict-go)",
    bg: "color-mix(in srgb, var(--ms-verdict-go) 18%, transparent)",
  },
  CONDITIONAL_GO: {
    color: "var(--ms-verdict-conditional-go)",
    bg: "color-mix(in srgb, var(--ms-verdict-conditional-go) 18%, transparent)",
  },
  NO_GO: {
    color: "var(--ms-verdict-no-go)",
    bg: "color-mix(in srgb, var(--ms-verdict-no-go) 18%, transparent)",
  },
  INSUFFICIENT_DATA: {
    color: "var(--ms-verdict-insufficient-data)",
    bg: "color-mix(in srgb, var(--ms-verdict-insufficient-data) 22%, transparent)",
  },
};

type Props = {
  verdicts: RecentVerdict[];
};

export function RecentVerdicts({ verdicts }: Props) {
  const { t, locale } = useLocale();

  return (
    <section
      className="rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
    >
      <h2
        className="text-sm font-semibold uppercase tracking-[0.14em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        {t("projects.recentVerdicts")}
      </h2>

      {verdicts.length === 0 ? (
        <p className="mt-4 text-sm" style={{ color: "var(--ms-text-muted)" }}>
          {t("projects.recentVerdictsEmpty")}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {verdicts.map((v) => {
            const style = VERDICT_STYLE[v.kind];
            return (
              <li
                key={v.id}
                className="rounded-lg border p-3"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-elevated)",
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p
                    className="text-sm font-medium"
                    style={{ color: "var(--ms-text-primary)" }}
                  >
                    {v.projectName}
                  </p>
                  <span
                    className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-wide"
                    style={{ color: style.color, background: style.bg }}
                  >
                    {labelVerdictType(locale, v.kind)}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
