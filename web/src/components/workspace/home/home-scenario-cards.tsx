"use client";

import { HOME_SCENARIOS, type HomeScenario } from "@/lib/home/home-scenarios";
import { useLocale } from "@/lib/i18n";

type Props = {
  onSelect: (scenario: HomeScenario) => void;
};

export function HomeScenarioCards({ onSelect }: Props) {
  const { t } = useLocale();
  return (
    <section data-testid="home-scenarios">
      <h2 className="text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
        {t("home.scenarios")}
      </h2>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {HOME_SCENARIOS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s)}
            className="rounded-lg border px-3 py-3 text-left text-sm transition-colors"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-surface)",
              color: "var(--ms-text-primary)",
            }}
            data-testid={`home-scenario-${s.id}`}
          >
            {t(s.labelKey)}
          </button>
        ))}
      </div>
    </section>
  );
}
