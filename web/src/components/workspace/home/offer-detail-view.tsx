"use client";

import type { ReactNode } from "react";
import type { OfferArtifactDetail } from "@/lib/api/endpoints/offers";
import { useLocale } from "@/lib/i18n";

type Props = {
  offer: OfferArtifactDetail;
};

function Section({
  title,
  children,
  testId,
  muted,
}: {
  title: string;
  children: ReactNode;
  testId?: string;
  muted?: boolean;
}) {
  if (!children || (Array.isArray(children) && children.length === 0)) return null;
  return (
    <div data-testid={testId}>
      <p className="text-sm font-semibold">{title}</p>
      <div
        className="mt-1 text-sm leading-relaxed"
        style={{ color: muted ? "var(--ms-text-muted)" : "var(--ms-text-secondary)" }}
      >
        {children}
      </div>
    </div>
  );
}

export function OfferDetailView({ offer }: Props) {
  const { t } = useLocale();

  return (
    <div className="grid gap-4 md:grid-cols-2" data-testid="offer-detail-view">
      <Section title={t("offer.fields.problem")} testId="offer-problem">
        {offer.problem_statement}
      </Section>
      <Section title={t("offer.fields.outcome")} testId="offer-outcome">
        {offer.promised_outcome}
      </Section>
      <Section title={t("offer.fields.value")} testId="offer-value">
        {offer.value_proposition}
      </Section>
      <Section title={t("offer.fields.cta")} testId="offer-cta">
        {offer.cta}
      </Section>

      {offer.offer_components.length > 0 ? (
        <Section title={t("offer.fields.components")} testId="offer-components">
          <ul className="list-disc space-y-1 pl-5">
            {offer.offer_components.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {offer.proof_references.length > 0 ? (
        <Section title={t("offer.fields.proof")} testId="offer-proof">
          <ul className="list-disc space-y-1 pl-5">
            {offer.proof_references.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {offer.conditions.length > 0 ? (
        <Section title={t("offer.fields.conditions")} testId="offer-conditions">
          <ul className="list-disc space-y-1 pl-5">
            {offer.conditions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {offer.unsupported_claims.length > 0 ? (
        <Section title={t("offer.fields.unsupported")} testId="offer-unsupported" muted>
          <ul className="list-disc space-y-1 pl-5">
            {offer.unsupported_claims.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {offer.evidence_gaps.length > 0 ? (
        <Section title={t("offer.fields.gaps")} testId="offer-gaps" muted>
          <ul className="list-disc space-y-1 pl-5">
            {offer.evidence_gaps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {(offer.upstream_sources ?? []).some(
        (source) => source.source_mode === "bridged_biv_snapshot",
      ) ? (
        <div
          className="md:col-span-2 rounded-lg border px-4 py-3 text-sm"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "color-mix(in srgb, var(--ms-brand-primary) 6%, var(--ms-bg-surface))",
          }}
          data-testid="offer-upstream-bridge-notice"
        >
          <p className="font-semibold">{t("offer.upstream.bridgeTitle")}</p>
          <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
            {t("offer.upstream.bridgeBody")}
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5" data-testid="offer-upstream-bridge-list">
            {(offer.upstream_sources ?? [])
              .filter((source) => source.source_mode === "bridged_biv_snapshot")
              .map((source) => (
                <li key={source.artifact_type}>
                  {t(`offer.upstream.artifact.${source.artifact_type}`)} —{" "}
                  {t("offer.upstream.bridgedLabel")}
                </li>
              ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
