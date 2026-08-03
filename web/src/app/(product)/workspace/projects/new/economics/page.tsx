"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepEconomicsForm } from "@/components/project-intake/steps/step-economics-form";

export default function IntakeEconomicsPage() {
  return (
    <IntakeWizardShell stepId="economics">
      <StepEconomicsForm />
    </IntakeWizardShell>
  );
}
