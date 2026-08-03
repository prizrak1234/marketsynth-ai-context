"use client";

import { useIntakeDraft } from "@/components/project-intake/intake-draft-context";
import { useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";

export function IntakeAutosaveIndicator() {
  const { saveStatus } = useIntakeDraft();
  const copy = useIntakeWizardCopy();

  if (saveStatus === "idle") return null;

  const label =
    saveStatus === "saving"
      ? copy.autosave.saving
      : saveStatus === "saved"
        ? copy.autosave.saved
        : copy.autosave.error;

  return (
    <p
      className="text-xs"
      role="status"
      aria-live="polite"
      data-testid="intake-autosave-status"
      style={{
        color:
          saveStatus === "error"
            ? "var(--ms-status-danger)"
            : "var(--ms-text-muted)",
      }}
    >
      {label}
    </p>
  );
}
