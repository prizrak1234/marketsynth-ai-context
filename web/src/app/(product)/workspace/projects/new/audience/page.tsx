"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepAudienceForm } from "@/components/project-intake/steps/step-audience-form";

export default function IntakeAudiencePage() {
  return (
    <IntakeWizardShell stepId="audience">
      <StepAudienceForm />
    </IntakeWizardShell>
  );
}
