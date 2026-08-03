"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepBasicsForm } from "@/components/project-intake/steps/step-basics-form";

export default function IntakeBasicsPage() {
  return (
    <IntakeWizardShell stepId="basics">
      <StepBasicsForm />
    </IntakeWizardShell>
  );
}
