"use client";

import { HOME_SCENARIOS, type HomeScenario } from "@/lib/home/home-scenarios";
import { useLocale } from "@/lib/i18n";

type Props = {
  onSelect: (scenario: HomeScenario) => void;
};

/** Agency Home: popular entrepreneur tasks (seed input only). */
export function HomePopularTasks({ onSelect }: Props) {
  const { t } = useLocale();
  const popular = HOME_SCENARIOS.filter((s) =>
    [
      "idea_validation",
      "market_research",
      "marketing_strategy",
      "youtube",
      "telegram_bot",
      "saas",
      "website",
      "other",
    ].includes(s.id),
  );

  return (
    <section data-testid="home-popular-tasks">
      <h2 className="text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
        {t("agency.popularTasks")}
      </h2>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {popular.map((s) => (
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
