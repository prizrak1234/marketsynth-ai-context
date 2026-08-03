"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepMarketForm } from "@/components/project-intake/steps/step-market-form";

export default function IntakeMarketPage() {
  return (
    <IntakeWizardShell stepId="market">
      <StepMarketForm />
    </IntakeWizardShell>
  );
}
