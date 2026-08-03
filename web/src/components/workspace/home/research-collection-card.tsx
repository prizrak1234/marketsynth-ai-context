"use client";

import type {
  BackendResearchSourceCandidate,
  BackendUserRequestDto,
} from "@/lib/api/types/user-requests";
import { useLocale } from "@/lib/i18n";

type Research = NonNullable<BackendUserRequestDto["research_collection"]>;

type Props = {
  research: Research;
};

function authorityLabel(t: (key: string) => string, v?: string): string {
  const key = `agency.research.authority.${v || "unknown"}`;
  const text = t(key);
  return text === key ? t("agency.research.authority.unknown") : text;
}

function freshnessLabel(t: (key: string) => string, v?: string): string {
  const key = `agency.research.freshness.${v || "unknown"}`;
  const text = t(key);
  return text === key ? t("agency.research.freshness.unknown") : text;
}

/** Commercial research results — no backend jargon. */
export function ResearchCollectionCard({ research }: Props) {
  const { t } = useLocale();
  const candidates = research.source_candidates ?? [];
  const report = research.retrieval_report ?? {};
  const coverage = research.provider_coverage;

  return (
    <div
      className="mt-3 space-y-3 rounded-lg border p-3 text-sm"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="home-research-card"
    >
      <p className="font-semibold">{t("agency.research.resultsTitle")}</p>
      {research.research_summary ? (
        <p className="whitespace-pre-wrap text-xs" style={{ color: "var(--ms-text-secondary)" }}>
          {research.research_summary}
        </p>
      ) : null}
      <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
        {t("agency.research.stats", {
          sources: String(report.candidate_count ?? candidates.length),
          duplicates: String(report.duplicate_count ?? 0),
          contradictions: String(
            report.contradiction_count ?? research.contradictions?.length ?? 0,
          ),
          gaps: String(report.missing_data_count ?? research.missing_data?.length ?? 0),
        })}
      </p>
      {coverage?.disclosure_ru ? (
        <p
          className="text-xs"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="home-research-limitations"
        >
          {t("agency.research.limitations")}: {coverage.disclosure_ru}
        </p>
      ) : null}
      {research.contradiction_note && !(research.contradictions?.length) ? (
        <p className="text-xs" data-testid="home-research-no-contradictions">
          {research.contradiction_note}
        </p>
      ) : null}
      {(research.contradictions?.length ?? 0) > 0 ? (
        <div data-testid="home-research-contradictions">
          <p className="text-xs font-semibold">{t("agency.research.contradictions")}</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-xs">
            {(research.contradictions as Array<{ topic?: string; conflicting_statements?: string[] }>).map(
              (c, i) => (
                <li key={i}>
                  {c.topic || t("agency.research.contradictionFallback")}
                  {(c.conflicting_statements || []).length
                    ? `: ${(c.conflicting_statements || []).join(" ↔ ")}`
                    : ""}
                </li>
              ),
            )}
          </ul>
        </div>
      ) : null}
      <ul className="space-y-2" data-testid="home-research-sources">
        {candidates.map((c: BackendResearchSourceCandidate, idx: number) => (
          <li
            key={c.id || c.url || idx}
            className="rounded border p-2 text-xs"
            style={{ borderColor: "var(--ms-border-default)" }}
            data-testid={`home-research-source-${idx}`}
          >
            <p className="font-medium">
              {c.title || c.publisher || t("agency.research.sourceUntitled")}
            </p>
            <p style={{ color: "var(--ms-text-muted)" }}>
              {[
                c.publisher,
                c.published_at?.slice?.(0, 10),
                authorityLabel(t, c.authority_level),
                freshnessLabel(t, c.freshness),
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {c.url ? (
              <a
                href={c.url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-block break-all underline"
              >
                {c.url}
              </a>
            ) : null}
          </li>
        ))}
      </ul>
      {(research.missing_data?.length ?? 0) > 0 ? (
        <p className="text-xs" data-testid="home-research-missing">
          {t("agency.research.missingData")}: {research.missing_data!.join(" ")}
        </p>
      ) : null}
    </div>
  );
}
