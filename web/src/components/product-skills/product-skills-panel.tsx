"use client";

import { useCallback, useEffect, useState } from "react";
import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import {
  fetchProductSkills,
  type ProductSkillIndexItem,
} from "@/lib/api/endpoints/product-skills";
import { useLocale } from "@/lib/i18n";

function statusLabel(skill: ProductSkillIndexItem, locale: string): string {
  if (!skill.enabled) return locale === "en" ? "Disabled" : "Отключён";
  if (skill.install_status === "installed_unconfigured" || !skill.configured) {
    return locale === "en" ? "Needs connection" : "Требуется подключить";
  }
  if (skill.install_status === "installed" || skill.install_status === "ready") {
    return locale === "en" ? "Available" : "Доступен";
  }
  return skill.install_status;
}

export function ProductSkillsPanel() {
  const { locale } = useLocale();
  const [skills, setSkills] = useState<ProductSkillIndexItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchProductSkills();
      setSkills(rows);
    } catch {
      setError(
        locale === "en"
          ? "Could not load skills"
          : "Не удалось загрузить навыки",
      );
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <div className="space-y-6" data-testid="product-skills-panel">
      <CommercialPageHeader
        title={locale === "en" ? "Skills & integrations" : "Навыки и интеграции"}
        description={
          locale === "en"
            ? "Product skills used by Marketsynth for content and research. Secrets stay in project settings — never inside packages."
            : "Навыки Marketsynth для контента и исследований. Секреты хранятся в настройках проекта — не в пакетах."
        }
        testId="product-skills-header"
      />
      {error ? (
        <CommercialAlert tone="danger" title={error} testId="product-skills-error" />
      ) : null}
      {loading ? (
        <CommercialLoadingState
          label={locale === "en" ? "Loading…" : "Загрузка…"}
        />
      ) : null}
      <div className="grid gap-4" data-testid="product-skills-list">
        {skills.map((skill) => (
          <CommercialCard key={skill.skill_id}>
            <div
              className="flex flex-col gap-2"
              data-testid={`product-skill-${skill.skill_id}`}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-lg font-semibold">{skill.name}</h3>
                <span
                  className="text-sm"
                  style={{ color: "var(--ms-text-secondary)" }}
                  data-testid={`product-skill-status-${skill.skill_id}`}
                >
                  {statusLabel(skill, locale)}
                </span>
              </div>
              <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {skill.description}
              </p>
              <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                v{skill.version} · {skill.type}
                {skill.last_run_status
                  ? ` · last: ${skill.last_run_status}`
                  : ""}
              </p>
              {skill.skill_id === "marketsynth.avito" && !skill.configured ? (
                <CommercialAlert
                  tone="warning"
                  title={
                    skill.safe_error
                      ? skill.safe_error
                      : locale === "en"
                        ? "Avito live API is not enabled yet"
                        : "Live API Avito пока не включён"
                  }
                />
              ) : skill.safe_error ? (
                <CommercialAlert tone="danger" title={skill.safe_error} />
              ) : null}
            </div>
          </CommercialCard>
        ))}
      </div>
    </div>
  );
}
