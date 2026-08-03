"use client";

import Link from "next/link";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialStatus } from "@/components/commercial/commercial-status";
import type { PccCapabilityCard } from "@/lib/api/endpoints/project-command-center";
import { useLocale } from "@/lib/i18n";

type Props = {
  cards: PccCapabilityCard[];
};

export function ProjectCapabilityGrid({ cards }: Props) {
  const { t } = useLocale();
  return (
    <section className="space-y-3" data-testid="project-capability-grid" id="pcc-capabilities">
      <h2 className="text-lg font-semibold" style={{ color: "var(--ms-text-primary)" }}>
        {t("projectCommandCenter.functionMenu")}
      </h2>
      <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        {t("projectCommandCenter.functionMenuHint")}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {cards.map((card) => (
          <CommercialCard
            key={card.capability_id}
            padding="sm"
            testId={`pcc-capability-${card.capability_id.replace(/\./g, "-")}`}
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold">{card.title}</h3>
              <CommercialStatus tone="neutral">{card.status_label}</CommercialStatus>
            </div>
            <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {card.value_proposition}
            </p>
            {card.last_result_summary ? (
              <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {t("projectCommandCenter.lastResult")}: {card.last_result_summary}
              </p>
            ) : null}
            {card.placeholder_note ? (
              <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {card.placeholder_note}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {card.cta_enabled && card.primary_cta_href && card.primary_cta_label ? (
                <CommercialButton
                  href={card.primary_cta_href}
                  testId={`pcc-capability-cta-${card.capability_id.replace(/\./g, "-")}`}
                >
                  {card.primary_cta_label}
                </CommercialButton>
              ) : null}
              {!card.cta_enabled ? (
                <span className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                  {t("projectCommandCenter.noActiveCta")}
                </span>
              ) : null}
              {card.secondary_cta_href && card.secondary_cta_label ? (
                <Link
                  href={card.secondary_cta_href}
                  className="text-sm underline underline-offset-2"
                  style={{ color: "var(--ms-text-accent, var(--ms-brand-primary))" }}
                >
                  {card.secondary_cta_label}
                </Link>
              ) : null}
            </div>
          </CommercialCard>
        ))}
      </div>
    </section>
  );
}
