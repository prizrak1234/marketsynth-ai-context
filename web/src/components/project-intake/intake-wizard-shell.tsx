"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import { IntakeAutosaveIndicator } from "@/components/project-intake/intake-autosave-indicator";
import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import { WorkspaceNav } from "@/components/workspace/workspace-nav";
import { PRODUCT_BRAND } from "@/lib/brand/product-brand";
import {
  INTAKE_STEPS,
  nextStepId,
  pathForStep,
  prevStepId,
} from "@/lib/project-intake/schema";
import {
  firstErrorFieldId,
  validateStep,
  type FieldErrors,
} from "@/lib/project-intake/validation";
import { useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";
import type { IntakeStepId } from "@/lib/project-intake/types";

const IntakeStepErrorsContext = createContext<FieldErrors>({});

export function useStepErrors(): FieldErrors {
  return useContext(IntakeStepErrorsContext);
}

type Props = {
  stepId: IntakeStepId;
  children: ReactNode;
};

export function IntakeWizardShell({ stepId, children }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const { draft, hydrated, setStep } = useIntakeDraft();
  const copy = useIntakeWizardCopy();
  const [errors, setErrors] = useState<FieldErrors>({});
  const [banner, setBanner] = useState<string | null>(null);

  useEffect(() => {
    setStep(stepId);
  }, [stepId, setStep]);

  const stepIndex = INTAKE_STEPS.findIndex((s) => s.id === stepId);

  const goNext = () => {
    const nextErrors = validateStep(stepId, draft);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      const first = firstErrorFieldId(nextErrors);
      if (first) {
        const el = document.getElementById(first);
        el?.focus();
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      setBanner(copy.shell.validationBanner);
      return;
    }
    setBanner(null);
    const next = nextStepId(stepId);
    if (next) router.push(pathForStep(next));
  };

  const goBack = () => {
    const prev = prevStepId(stepId);
    if (prev) router.push(pathForStep(prev));
    else router.push("/workspace");
  };

  if (!hydrated) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-muted)" }}
        data-testid="intake-wizard-loading"
      >
        <CommercialLoadingState label={copy.shell.loadingDraft} variant="inline" />
      </div>
    );
  }

  const stepProgress = copy.shell.stepProgress
    .replace("{current}", String(stepIndex + 1))
    .replace("{total}", String(INTAKE_STEPS.length));

  return (
    <div
      className="flex min-h-screen overflow-x-hidden"
      style={{ background: "var(--ms-bg-canvas)", color: "var(--ms-text-primary)" }}
      data-testid="intake-wizard-shell"
    >
      <WorkspaceNav />
      <div className="flex min-w-0 flex-1 flex-col overflow-x-hidden">
        <header
          className="border-b px-4 py-4 sm:px-8"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-surface)",
          }}
        >
          <CommercialPageHeader
            level="page"
            eyebrow={
              <span
                className="text-xs font-semibold uppercase tracking-[0.18em]"
                style={{ color: "var(--ms-brand-secondary)" }}
              >
                {PRODUCT_BRAND.displayName} · {copy.shell.eyebrow}
              </span>
            }
            title={copy.shell.title}
            description={copy.shell.subtitle}
            testId="intake-wizard-header"
          />
        </header>

        <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-8 sm:py-8 lg:flex-row lg:gap-8">
          <nav
            aria-label={copy.shell.stepsNav}
            className="hidden w-full shrink-0 lg:block lg:w-56"
            data-testid="intake-step-nav-desktop"
          >
            <ol className="space-y-1">
              {INTAKE_STEPS.map((s, i) => {
                const active = s.id === stepId || s.path === pathname;
                const done = i < stepIndex;
                return (
                  <li key={s.id}>
                    <Link
                      href={s.path}
                      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]"
                      aria-current={active ? "step" : undefined}
                      style={
                        active
                          ? {
                              background: "var(--ms-bg-elevated)",
                              color: "var(--ms-text-primary)",
                              boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                            }
                          : {
                              color: done
                                ? "var(--ms-text-secondary)"
                                : "var(--ms-text-muted)",
                            }
                      }
                    >
                      <span
                        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold"
                        style={{
                          background: active
                            ? "var(--ms-brand-primary)"
                            : done
                              ? "color-mix(in srgb, var(--ms-status-success) 35%, transparent)"
                              : "var(--ms-bg-elevated)",
                          color: active ? "var(--ms-text-on-brand, #fff)" : "var(--ms-text-primary)",
                        }}
                        aria-hidden
                      >
                        {done ? "✓" : i + 1}
                      </span>
                      <span>{s.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ol>
            <div className="mt-4 space-y-1">
              <p className="text-sm" style={{ color: "var(--ms-text-muted)" }}>
                {stepProgress}
              </p>
              <IntakeAutosaveIndicator />
              <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {copy.shell.autosaveHint}
              </p>
            </div>
          </nav>

          <div className="min-w-0 flex-1">
            <div
              className="mb-4 flex items-center justify-between gap-3 lg:hidden"
              data-testid="intake-step-nav-mobile"
            >
              <p className="text-sm font-medium" style={{ color: "var(--ms-text-primary)" }}>
                {INTAKE_STEPS[stepIndex]?.label}
              </p>
              <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                {stepProgress}
              </p>
            </div>
            <div className="mb-4 lg:hidden">
              <IntakeAutosaveIndicator />
            </div>

            {banner ? (
              <div className="mb-4">
                <CommercialAlert
                  tone="danger"
                  title={banner}
                  testId="intake-step-validation-banner"
                />
              </div>
            ) : null}

            <CommercialCard padding="lg" testId="intake-step-card">
              <IntakeStepErrorsContext.Provider value={errors}>
                {children}
              </IntakeStepErrorsContext.Provider>
            </CommercialCard>

            {stepId !== "review" ? (
              <div
                className="sticky bottom-0 mt-6 flex flex-col-reverse gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-canvas)",
                }}
                data-testid="intake-form-action-bar"
              >
                <CommercialButton variant="secondary" onClick={goBack} testId="intake-back">
                  {prevStepId(stepId) ? copy.shell.back : copy.shell.backToWorkspace}
                </CommercialButton>
                <CommercialButton onClick={goNext} testId="intake-next" className="min-h-[44px] px-6 py-3">
                  {copy.shell.next}
                </CommercialButton>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
