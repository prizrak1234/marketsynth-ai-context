"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepMaterialsForm } from "@/components/project-intake/steps/step-materials-form";

export default function IntakeMaterialsPage() {
  return (
    <IntakeWizardShell stepId="materials">
      <StepMaterialsForm />
    </IntakeWizardShell>
  );
}
