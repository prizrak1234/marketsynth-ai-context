"use client";

import { useMemo } from "react";

import { useLocale } from "@/lib/i18n";
import {
  intakeWizardCopyEn,
  intakeWizardCopyRu,
} from "@/lib/i18n/translations/intake-wizard-copy";
import type { IntakeStepId } from "@/lib/project-intake/types";

export function useIntakeWizardCopy() {
  const { locale } = useLocale();
  return useMemo(
    () => (locale === "en" ? intakeWizardCopyEn : intakeWizardCopyRu),
    [locale],
  );
}

export function useIntakeStepCopy(stepId: IntakeStepId) {
  const copy = useIntakeWizardCopy();
  return copy.steps[stepId];
}
