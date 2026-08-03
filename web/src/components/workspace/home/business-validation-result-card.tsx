"use client";

import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard, CommercialCardInset } from "@/components/commercial/commercial-card";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import { CommercialProgress } from "@/components/commercial/commercial-progress";
import { useLocale } from "@/lib/i18n";

import { BusinessValidationDeveloperPanel } from "./business-validation-developer-panel";

type Props = {
  result: BusinessIdeaValidationOutput;
  onCreateNewReport?: () => void;
  onRefineData?: () => void;
  busy?: boolean;
  migrationOnly?: boolean;
};

/** CWF.1 commercial research conclusion — Customer Report only. */
export function BusinessValidationResultCard({
  result,
  onCreateNewReport,
  onRefineData,
  busy,
  migrationOnly = false,
}: Props) {
  const { t } = useLocale();
  const report = result.customer_report;

  if (!report) {
    return (
      <CommercialCard testId="business-validation-result-card" researchUiState="legacy_report">
        <CommercialPageHeader
          level="panel"
          title={t("agency.biv.commercial.legacyTitle")}
          description={t("agency.biv.commercial.legacyExplanation")}
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {onCreateNewReport ? (
            <CommercialButton
              disabled={busy}
              onClick={onCreateNewReport}
              testId="biv-create-new-report"
            >
              {t("agency.biv.commercial.createNewReport")}
            </CommercialButton>
          ) : null}
          {!migrationOnly && onRefineData ? (
            <CommercialButton
              variant="secondary"
              disabled={busy}
              onClick={onRefineData}
              testId="biv-refine-from-legacy"
            >
              {t("agency.action.refineInputs")}
            </CommercialButton>
          ) : null}
        </div>
      </CommercialCard>
    );
  }

  const { executive_summary: exec, structured_verdict: verdict } = report;

  return (
    <CommercialCard testId="business-validation-result-card" className="space-y-6" researchUiState="completed">
      <span data-testid="biv-report-hydrated" className="sr-only" aria-hidden="true" />
      <CommercialPageHeader
        level="panel"
        eyebrow={
          <p className="text-xs uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
            {exec.title}
          </p>
        }
        title={exec.status_line}
        description={`${t("agency.biv.commercial.confidenceLabel")}: ${exec.confidence_percent}%`}
        testId="biv-executive-summary"
      />
      {exec.primary_risk ? (
        <CommercialCardInset testId="biv-primary-risk">
          <p className="text-sm">
            <span className="font-medium">{t("agency.biv.commercial.primaryRisk")}: </span>
            {exec.primary_risk}
          </p>
        </CommercialCardInset>
      ) : null}
      {exec.primary_advantage ? (
        <CommercialCardInset testId="biv-primary-advantage">
          <p className="text-sm">
            <span className="font-medium">{t("agency.biv.commercial.primaryAdvantage")}: </span>
            {exec.primary_advantage}
          </p>
        </CommercialCardInset>
      ) : null}

      <section data-testid="biv-confirmed-section">
        <p className="text-sm font-semibold">{t("agency.biv.commercial.confirmedTitle")}</p>
        {report.confirmed_findings.length > 0 ? (
          <ul className="mt-3 space-y-3">
            {report.confirmed_findings.map((item, idx) => (
              <li key={`${item.headline}-${idx}`}>
                <CommercialCardInset testId={`biv-confirmed-${idx}`}>
                  <p className="text-sm font-medium">✔ {item.headline}</p>
                  <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                    {item.explanation}
                  </p>
                  {item.sources.length > 0 ? (
                    <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {item.sources.map((s) => (
                        <li key={s.title}>
                          {t("agency.biv.source")}: {s.title}
                          {s.domain ? ` · ${s.domain}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </CommercialCardInset>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {t("agency.biv.commercial.confirmedEmpty")}
          </p>
        )}
      </section>

      {report.unconfirmed_topics.length > 0 ? (
        <section data-testid="biv-unconfirmed-section">
          <p className="text-sm font-semibold">{t("agency.biv.commercial.unconfirmedTitle")}</p>
          <ul className="mt-3 space-y-3">
            {report.unconfirmed_topics.map((topic) => (
              <li key={topic.topic}>
                <CommercialCardInset>
                  <p className="text-sm font-medium">
                    {t("agency.biv.commercial.unconfirmedPrefix")} {topic.topic}
                  </p>
                  <p className="mt-2 text-sm">
                    <span className="font-medium">{t("agency.biv.commercial.reason")}: </span>
                    {topic.reason}
                  </p>
                  {topic.methods_used.length > 0 ? (
                    <p className="mt-2 text-sm">
                      <span className="font-medium">{t("agency.biv.commercial.methodsUsed")}: </span>
                      {topic.methods_used.join("; ")}
                    </p>
                  ) : null}
                  <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                    {topic.result_summary}
                  </p>
                </CommercialCardInset>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section data-testid="biv-confidence-section">
        <p className="text-sm font-semibold">{t("agency.biv.commercial.confidenceBlockTitle")}</p>
        <div className="mt-3 space-y-3">
          {report.dimension_confidence.map((dim) => (
            <CommercialProgress
              key={dim.dimension_id}
              label={dim.label}
              value={dim.score}
              testId="biv-confidence-dimension"
            />
          ))}
          <CommercialCardInset testId="biv-overall-confidence">
            <p className="text-sm font-medium">
              {t("agency.biv.commercial.overallConfidence")}: {report.overall_confidence_percent}%
            </p>
          </CommercialCardInset>
        </div>
      </section>

      <section data-testid="biv-coverage-score">
        <p className="text-sm font-semibold">{t("agency.biv.commercial.coverageTitle")}</p>
        <p className="mt-1 text-2xl font-semibold">{report.coverage.overall_percent}%</p>
        {report.coverage.dimensions_researched.length > 0 ? (
          <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {t("agency.biv.commercial.coverageResearched")}:{" "}
            {report.coverage.dimensions_researched.join(" · ")}
          </p>
        ) : null}
      </section>

      {report.clarification_questions.length > 0 ? (
        <section data-testid="biv-clarification-questions">
          <p className="text-sm font-semibold">{t("agency.biv.commercial.clarificationTitle")}</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {report.clarification_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <CommercialCardInset testId="biv-structured-verdict">
        <p className="text-sm font-semibold">{t("agency.biv.commercial.verdictTitle")}</p>
        {verdict.confirmed_summary.length > 0 ? (
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-wide">
              {t("agency.biv.commercial.verdictConfirmed")}
            </p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {verdict.confirmed_summary.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {verdict.unconfirmed_summary.length > 0 ? (
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-wide">
              {t("agency.biv.commercial.verdictUnconfirmed")}
            </p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {verdict.unconfirmed_summary.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {verdict.risks.length > 0 ? (
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-wide">
              {t("agency.biv.commercial.verdictRisks")}
            </p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {verdict.risks.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {verdict.verification_needed.length > 0 ? (
          <div className="mt-3">
            <p className="text-xs font-semibold uppercase tracking-wide">
              {t("agency.biv.commercial.verdictVerify")}
            </p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {verdict.verification_needed.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="mt-4 text-sm font-medium">{verdict.recommendation}</p>
        <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
          {t("agency.biv.commercial.verdictConfidence")}: {verdict.confidence_percent}%
        </p>
      </CommercialCardInset>

      <BusinessValidationDeveloperPanel result={result} />
    </CommercialCard>
  );
}
