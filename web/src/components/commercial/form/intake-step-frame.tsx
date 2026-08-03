import type { ReactNode } from "react";

import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import { CommercialFieldGroup } from "@/components/commercial/form/commercial-field-group";

type IntakeStepFrameProps = {
  title: string;
  description: string;
  children: ReactNode;
  testId?: string;
  footer?: ReactNode;
};

/** Canonical step scaffold: header → required body → optional footer (Slice E). */
export function IntakeStepFrame({
  title,
  description,
  children,
  testId,
  footer,
}: IntakeStepFrameProps) {
  return (
    <section className="space-y-6" data-testid={testId}>
      <CommercialPageHeader
        level="panel"
        title={title}
        description={description}
        testId={testId ? `${testId}-header` : undefined}
      />
      <CommercialFieldGroup testId={testId ? `${testId}-fields` : undefined}>
        {children}
      </CommercialFieldGroup>
      {footer}
    </section>
  );
}
