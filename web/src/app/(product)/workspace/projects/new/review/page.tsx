"use client";

import { IntakeWizardShell } from "@/components/project-intake/intake-wizard-shell";
import { StepReviewForm } from "@/components/project-intake/steps/step-review-form";

export default function IntakeReviewPage() {
  return (
    <IntakeWizardShell stepId="review">
      <StepReviewForm />
    </IntakeWizardShell>
  );
}
