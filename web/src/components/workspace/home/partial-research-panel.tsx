"use client";

import type { BusinessIdeaValidationOutput } from "@/lib/api/types/business-idea-validation";
import { useLocale } from "@/lib/i18n";
import { buildPartialResearchPanelViewModel } from "@/lib/biv/partial-research-view-model";
import { CommercialBadge } from "@/components/commercial/commercial-badge";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard, CommercialCardInset } from "@/components/commercial/commercial-card";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";

type PartialResearchPanelProps = {
  output: BusinessIdeaValidationOutput;
  busy?: boolean;
  canRerun?: boolean;
  onRerun?: () => void;
  onBackToIdea?: () => void;
};

export function PartialResearchPanel({
  output,
  busy = false,
  canRerun = false,
  onRerun,
  onBackToIdea,
}: PartialResearchPanelProps) {
  const { t } = useLocale();
  const vm = buildPartialResearchPanelViewModel(output, t);

  if (!vm) {
    return null;
  }

  return (
    <CommercialCard testId="biv-partial-research-panel" className="space-y-5">
      <CommercialPageHeader
        level="panel"
        eyebrow={
          <CommercialBadge tone="warning" uppercase>
            {t("agency.biv.partialResearch.badge")}
          </CommercialBadge>
        }
        title={t("agency.biv.partialResearch.title")}
        description={vm.interimConclusion ?? t("agency.biv.partialResearch.summary")}
        testId="biv-partial-research-title"
      />

      <CommercialCardInset testId="biv-partial-stop-reason">
        <h3 className="text-sm font-semibold">{t("agency.biv.stopReasonTitle")}</h3>
        <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {vm.stopReasonText}
        </p>
      </CommercialCardInset>

      {vm.establishedFindings.length > 0 ? (
        <div data-testid="biv-partial-established">
          <h3 className="text-sm font-semibold">{t("agency.biv.partialResearch.establishedTitle")}</h3>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {vm.establishedFindings.map((item, index) => (
              <li key={`est-${index}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {vm.hasFindingsSection ? (
        <div data-testid="biv-partial-findings">
          <h3 className="text-sm font-semibold">{t("agency.biv.findings")}</h3>
          <ul className="mt-2 space-y-3">
            {vm.findings.map((finding) => (
              <li
                key={finding.id}
              >
                <CommercialCardInset testId={`biv-partial-finding-${finding.id}`}>
                  <p className="text-sm font-medium">{finding.title}</p>
                {finding.category ? (
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {finding.category}
                  </p>
                ) : null}
                {finding.summary ? (
                  <p className="mt-2 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                    {finding.summary}
                  </p>
                ) : null}
                {finding.confidencePercent !== null ||
                finding.linkedEvidenceCount > 0 ? (
                  <p className="mt-2 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {[
                      finding.confidencePercent !== null
                        ? t("agency.biv.confidence", {
                            score: String(finding.confidencePercent),
                          })
                        : null,
                      finding.linkedEvidenceCount > 0
                        ? t("agency.biv.partialResearch.linkedSources", {
                            count: String(finding.linkedEvidenceCount),
                          })
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                ) : null}
                </CommercialCardInset>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p
          className="text-sm"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="biv-partial-findings-empty"
        >
          {t("agency.biv.partialResearch.noFindings")}
        </p>
      )}

      {vm.hasEvidenceSection ? (
        <div data-testid="biv-partial-evidence">
          <h3 className="text-sm font-semibold">{t("agency.biv.sources")}</h3>
          <ul className="mt-2 space-y-3">
            {vm.evidence.map((item) => (
              <li
                key={item.id}
                className="rounded-lg border p-3 break-words"
                style={{ borderColor: "var(--ms-border-default)" }}
              >
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium underline-offset-2 hover:underline"
                    style={{ color: "var(--ms-brand-primary)" }}
                  >
                    {item.title}
                  </a>
                ) : (
                  <p className="text-sm font-medium">{item.title}</p>
                )}
                {item.claim ? (
                  <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
                    {item.claim}
                  </p>
                ) : null}
                {item.excerpt ? (
                  <p className="mt-1 text-xs break-words" style={{ color: "var(--ms-text-muted)" }}>
                    {item.excerpt}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {vm.hasGapsSection ? (
        <div data-testid="biv-partial-gaps">
          <h3 className="text-sm font-semibold">{t("agency.biv.missingDataTitle")}</h3>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {vm.gaps.map((gap) => (
              <li key={gap.code}>
                <span>{gap.message}</span>
                {gap.action ? (
                  <p className="mt-1 text-xs" style={{ color: "var(--ms-text-muted)" }}>
                    {gap.action}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {vm.hasRemediationSection ? (
        <div data-testid="biv-partial-remediation">
          <h3 className="text-sm font-semibold">
            {t("agency.biv.partialResearch.remediationTitle")}
          </h3>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {vm.remediationQuestions.map((item, index) => (
              <li key={`${item.question}-${index}`}>{item.question}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {vm.hasLimitationsSection ? (
        <div data-testid="biv-partial-limitations">
          <h3 className="text-sm font-semibold">{t("agency.biv.partialResearch.limitationsTitle")}</h3>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {vm.limitations.map((item, index) => (
              <li key={`lim-${index}`}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {vm.hasNextStepsSection ? (
        <div data-testid="biv-partial-next-steps">
          <h3 className="text-sm font-semibold">{t("agency.biv.partialResearch.nextStepsTitle")}</h3>
          <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {vm.nextSteps.map((step) => (
              <li key={step.id}>{step.label}</li>
            ))}
          </ol>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 pt-1" data-testid="biv-partial-actions">
        {canRerun && onRerun ? (
          <CommercialButton
            variant="primary"
            disabled={busy}
            onClick={onRerun}
            testId="biv-partial-rerun"
          >
            {t("agency.action.retryResearch")}
          </CommercialButton>
        ) : null}
        {onBackToIdea ? (
          <CommercialButton
            variant="secondary"
            disabled={busy}
            onClick={onBackToIdea}
            testId="biv-partial-back-to-idea"
          >
            {t("agency.biv.partialResearch.backToIdea")}
          </CommercialButton>
        ) : null}
      </div>
    </CommercialCard>
  );
}
