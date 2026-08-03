"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCardInset } from "@/components/commercial/commercial-card";
import { CommercialStatus } from "@/components/commercial/commercial-status";
import { IntakeDeveloperDiagnostics } from "@/components/project-intake/intake-developer-diagnostics";
import { StepSection } from "@/components/project-intake/intake-fields";
import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import {
  executeIntakeBriefGoldenPath,
  workspaceUrlAfterGoldenPath,
} from "@/lib/integration/intake-brief-golden-path";
import { getIntegrationMode } from "@/lib/integration/mode";
import {
  isProjectSyncInFlight,
  reconcileIntakeProject,
  verifyIntakeBackendProjectBinding,
} from "@/lib/integration/project-sync";
import {
  customerAudienceModelLabel,
  customerBusinessTypeLabel,
  customerClarifications,
  customerProjectStageLabel,
  customerReadinessLabel,
  formatMoneyValue,
  readinessStatusTone,
} from "@/lib/project-intake/customer-readiness";
import {
  canStartInvestigation,
  evaluateIntakeReadiness,
} from "@/lib/project-intake/readiness";
import { pathForStep } from "@/lib/project-intake/schema";
import { useIntakeStepCopy, useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-4">
      <dt className="text-sm font-medium" style={{ color: "var(--ms-text-muted)" }}>
        {label}
      </dt>
      <dd className="text-base leading-relaxed break-words" style={{ color: "var(--ms-text-primary)" }}>
        {value.trim() ? value : "—"}
      </dd>
    </div>
  );
}

function SummarySection({ title, children, testId }: { title: string; children: ReactNode; testId: string }) {
  return (
    <CommercialCardInset testId={testId}>
      <section className="space-y-3">
        <h3 className="text-base font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {title}
        </h3>
        <dl className="space-y-3">{children}</dl>
      </section>
    </CommercialCardInset>
  );
}

export function StepReviewForm() {
  const router = useRouter();
  const { draft, setDraft } = useIntakeDraft();
  const stepCopy = useIntakeStepCopy("review");
  const wizardCopy = useIntakeWizardCopy();
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const mode = getIntegrationMode();

  const readiness = useMemo(() => evaluateIntakeReadiness(draft), [draft]);
  const canStart = canStartInvestigation(readiness);
  const busy = submitting || isProjectSyncInFlight(draft.id);
  const clarifications = customerClarifications(readiness);

  useEffect(() => {
    if (mode === "mock") return;
    let cancelled = false;
    void (async () => {
      const next = await verifyIntakeBackendProjectBinding(draft);
      if (cancelled) return;
      const prevSync = draft.backendSync;
      const nextSync = next.backendSync;
      if (
        prevSync?.backendProjectId !== nextSync?.backendProjectId ||
        prevSync?.lastSyncError !== nextSync?.lastSyncError ||
        prevSync?.backendSyncState !== nextSync?.backendSyncState
      ) {
        setDraft(() => next);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [draft.id, mode, setDraft]);

  const onStart = async () => {
    if (busy) return;
    const latest = evaluateIntakeReadiness(draft);
    setDraft((prev) => ({ ...prev, readiness: latest }));
    if (!canStartInvestigation(latest)) {
      setNotice(wizardCopy.review.notReadyNotice);
      return;
    }

    if (mode === "mock") {
      setNotice(wizardCopy.review.mockModeNotice);
      return;
    }

    setSubmitting(true);
    setNotice(null);
    try {
      const withReady = { ...draft, readiness: latest };
      const result = await executeIntakeBriefGoldenPath(withReady);
      setDraft(() => result.draft);
      if (!result.ok) {
        setNotice(`${result.message} ${result.actionHint}`);
        return;
      }
      router.push(workspaceUrlAfterGoldenPath(result.projectId));
    } catch {
      setNotice(wizardCopy.review.submitError);
    } finally {
      setSubmitting(false);
    }
  };

  const onReconcile = async () => {
    if (busy) return;
    setSubmitting(true);
    try {
      const result = await reconcileIntakeProject(draft);
      setDraft(() => result.draft);
      if (!result.ok) {
        setNotice(`${result.error.message} ${result.error.actionHint}`);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const b = draft.projectBasics;
  const p = draft.product;
  const m = draft.market;
  const a = draft.audience;
  const e = draft.economics;
  const mat = draft.materials;
  const showReconcile =
    mode !== "mock" &&
    (draft.backendSync?.backendSyncState === "conflict" ||
      draft.backendSync?.backendSyncState === "failed");

  return (
    <StepSection
      title={stepCopy.title}
      description={stepCopy.description}
      data-testid="intake-review-customer"
    >
      <CommercialCardInset testId="intake-readiness-status">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="text-sm font-medium" style={{ color: "var(--ms-text-muted)" }}>
              {wizardCopy.review.readinessTitle}
            </p>
            <p className="text-xl font-semibold tracking-tight" style={{ color: "var(--ms-text-primary)" }}>
              {customerReadinessLabel(readiness.status)}
            </p>
          </div>
          <CommercialStatus tone={readinessStatusTone(readiness.status)} testId="intake-readiness-chip">
            {customerReadinessLabel(readiness.status)}
          </CommercialStatus>
        </div>
      </CommercialCardInset>

      <div className="space-y-4">
        <SummarySection title={wizardCopy.review.sections.project} testId="intake-review-section-project">
          <SummaryRow label="Название" value={b.name} />
          <SummaryRow label="Описание идеи" value={b.ideaDescription} />
          <SummaryRow label="Тип бизнеса" value={customerBusinessTypeLabel(b.businessType)} />
          <SummaryRow label="Стадия" value={customerProjectStageLabel(b.projectStage)} />
          <SummaryRow label="География" value={b.geography} />
        </SummarySection>

        <SummarySection title={wizardCopy.review.sections.product} testId="intake-review-section-product">
          <SummaryRow label="Что продаётся" value={p.whatIsSold} />
          <SummaryRow label="Проблема клиента" value={p.primaryProblem} />
          <SummaryRow label="Ценность" value={p.valueProposition} />
          <SummaryRow label="Цена" value={formatMoneyValue(p.price, p.priceUnknown)} />
        </SummarySection>

        <SummarySection title={wizardCopy.review.sections.market} testId="intake-review-section-market">
          <SummaryRow label="Рынок" value={m.targetMarket} />
          <SummaryRow label="География" value={m.geography || b.geography} />
          <SummaryRow
            label="Конкуренты"
            value={m.competitorsUnknown ? "Пока не указаны" : m.knownCompetitors}
          />
        </SummarySection>

        <SummarySection title={wizardCopy.review.sections.audience} testId="intake-review-section-audience">
          <SummaryRow label="Модель клиентов" value={customerAudienceModelLabel(a.customerModel)} />
          <SummaryRow
            label="Сегменты"
            value={
              a.segments
                .filter((s) => s.label.trim())
                .map((s) => s.label)
                .join("; ") || "—"
            }
          />
          <SummaryRow label="Боли аудитории" value={a.expectedPains} />
        </SummarySection>

        <SummarySection title={wizardCopy.review.sections.economics} testId="intake-review-section-economics">
          <SummaryRow label="Бюджет запуска" value={formatMoneyValue(e.launchBudget)} />
          <SummaryRow label="Маркетинг в месяц" value={formatMoneyValue(e.monthlyMarketingBudget)} />
          <SummaryRow label="Ограничения" value={e.criticalConstraints} />
        </SummarySection>

        <SummarySection title={wizardCopy.review.sections.materials} testId="intake-review-section-materials">
          <SummaryRow label="Сайт" value={mat.websiteUrl} />
          <SummaryRow
            label="Вложения"
            value={
              mat.items.length
                ? mat.items.map((i) => i.label).join(", ")
                : "Пока не добавлены"
            }
          />
        </SummarySection>

        {clarifications.length > 0 ? (
          <CommercialAlert
            tone="warning"
            title={wizardCopy.review.clarificationsTitle}
            message={clarifications.join(" · ")}
            testId="intake-clarifications"
          />
        ) : null}
      </div>

      {notice ? (
        <CommercialAlert tone="danger" title={notice} testId="intake-review-notice" />
      ) : null}

      <div
        className="sticky bottom-0 flex flex-col-reverse gap-3 border-t pt-4 sm:flex-row sm:flex-wrap sm:items-center"
        style={{ borderColor: "var(--ms-border-default)" }}
        data-testid="intake-review-actions"
      >
        <CommercialButton
          variant="secondary"
          href={pathForStep("basics")}
          testId="intake-review-back-edit"
          className="min-h-[44px] px-6 py-3"
        >
          {wizardCopy.review.backEdit}
        </CommercialButton>
        <CommercialButton
          onClick={() => void onStart()}
          disabled={!canStart || busy || mode === "mock"}
          testId="intake-golden-path-submit"
          className="min-h-[44px] px-6 py-3"
        >
          {busy ? wizardCopy.review.starting : wizardCopy.review.startResearch}
        </CommercialButton>
      </div>

      <IntakeDeveloperDiagnostics
        draft={draft}
        onReconcile={() => void onReconcile()}
        reconcileBusy={busy}
        showReconcile={showReconcile}
      />
    </StepSection>
  );
}
