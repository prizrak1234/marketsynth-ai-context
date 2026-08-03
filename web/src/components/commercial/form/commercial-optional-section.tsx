"use client";

import { useState, type ReactNode } from "react";

import { CommercialCardInset } from "@/components/commercial/commercial-card";
import { useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";

type CommercialOptionalSectionProps = {
  children: ReactNode;
  /** When true, section starts expanded (e.g. filled optional values). */
  defaultOpen?: boolean;
  testId?: string;
};

/** Collapsible optional field group — does not affect validation. */
export function CommercialOptionalSection({
  children,
  defaultOpen = false,
  testId = "intake-optional-section",
}: CommercialOptionalSectionProps) {
  const copy = useIntakeWizardCopy();
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="space-y-3" data-testid={testId}>
      <button
        type="button"
        className="flex w-full items-center justify-between rounded-md px-1 py-1 text-left text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{ color: "var(--ms-text-secondary)" }}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        data-testid={`${testId}-toggle`}
      >
        <span>{copy.optionalSection.title}</span>
        <span className="text-xs font-normal" style={{ color: "var(--ms-text-muted)" }}>
          {open ? copy.optionalSection.toggleHide : copy.optionalSection.toggleShow}
        </span>
      </button>
      {open ? (
        <CommercialCardInset testId={`${testId}-body`}>
          <div className="space-y-5">{children}</div>
        </CommercialCardInset>
      ) : null}
    </section>
  );
}
