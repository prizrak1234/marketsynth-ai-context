"use client";

import type { AgencyVerdictView } from "@/lib/home/agency-analysis-flow";
import { useLocale } from "@/lib/i18n";

type Props = {
  verdict: AgencyVerdictView;
  sourcesCount?: number;
};

export function AgencyVerdictCard({ verdict, sourcesCount = 0 }: Props) {
  const { t } = useLocale();
  const toneLabel =
    verdict.tone === "go"
      ? `🟢 ${t(verdict.titleKey)}`
      : verdict.tone === "conditional"
        ? `🟡 ${t(verdict.titleKey)}`
        : verdict.tone === "insufficient_data"
          ? `⚪ ${t(verdict.titleKey)}`
          : `🔴 ${t(verdict.titleKey)}`;

  const whyText = verdict.whyKey ? t(verdict.whyKey) : verdict.why;

  return (
    <article
      className="space-y-4 rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="agency-verdict-card"
      data-tone={verdict.tone}
      data-research-working={verdict.evidence.researchWorking ? "true" : "false"}
    >
      <header>
        <p
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: "var(--ms-text-muted)" }}
        >
          {t("agency.verdictLabel")}
        </p>
        <h3
          className="mt-1 text-2xl font-bold"
          style={{ color: "var(--ms-text-primary)" }}
          data-testid="agency-verdict-title"
        >
          {toneLabel}
        </h3>
        {!verdict.evidence.hasEvidence ? (
          <p
            className="mt-2 text-sm"
            style={{ color: "var(--ms-danger, #b42318)" }}
            data-testid="agency-research-not-done"
          >
            {t("agency.research.notExecuted")}
          </p>
        ) : null}
      </header>

      <section>
        <h4 className="text-sm font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {t("agency.verdict.why")}
        </h4>
        <p
          className="mt-1 whitespace-pre-wrap text-sm leading-relaxed"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="agency-verdict-why"
        >
          {whyText.length > 900 ? `${whyText.slice(0, 897)}…` : whyText}
        </p>
        {!verdict.evidence.hasEvidence ? (
          <p
            className="mt-2 text-sm"
            style={{ color: "var(--ms-text-muted)" }}
            data-testid="agency-research-block-reason"
          >
            {t(verdict.evidence.blockReasonKey)}
          </p>
        ) : null}
      </section>

      {verdict.showMetrics ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Block
              title={t("agency.verdict.risks")}
              items={verdict.risks}
              empty={t("agency.verdict.noneListed")}
            />
            <Block
              title={t("agency.verdict.strengths")}
              items={verdict.strengths}
              empty={t("agency.verdict.noneListed")}
            />
          </div>

          <section>
            <h4 className="text-sm font-semibold">{t("agency.verdict.economics")}</h4>
            <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
              {verdict.economics}
            </p>
          </section>

          <section className="grid gap-3 sm:grid-cols-2">
            <div>
              <h4 className="text-sm font-semibold">{t("agency.verdict.successChance")}</h4>
              <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {t(verdict.successChance)}
              </p>
            </div>
            <div>
              <h4 className="text-sm font-semibold">{t("agency.verdict.sources")}</h4>
              <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                {t(verdict.sourcesNote, { count: String(sourcesCount) })}
              </p>
            </div>
          </section>
        </>
      ) : null}

      {verdict.whatToChange.length > 0 ? (
        <Block
          title={t("agency.verdict.whatToChange")}
          items={verdict.whatToChange}
          empty=""
        />
      ) : null}
    </article>
  );
}

function Block({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <section>
      <h4 className="text-sm font-semibold">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-1 text-sm" style={{ color: "var(--ms-text-muted)" }}>
          {empty}
        </p>
      ) : (
        <ul
          className="mt-1 list-disc space-y-1 pl-5 text-sm"
          style={{ color: "var(--ms-text-secondary)" }}
        >
          {items.map((item) => (
            <li key={item.slice(0, 48)}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
