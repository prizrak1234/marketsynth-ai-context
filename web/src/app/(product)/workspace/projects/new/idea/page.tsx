"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepProductForm } from "@/components/project-intake/steps/step-product-form";

export default function IntakeIdeaPage() {
  return (
    <IntakeWizardShell stepId="product">
      <StepProductForm />
    </IntakeWizardShell>
  );
}
