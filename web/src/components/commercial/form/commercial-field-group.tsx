import type { ReactNode } from "react";

type CommercialFieldGroupProps = {
  children: ReactNode;
  className?: string;
  testId?: string;
};

/** Groups related fields with consistent vertical rhythm (DESIGN.md §5). */
export function CommercialFieldGroup({
  children,
  className = "",
  testId,
}: CommercialFieldGroupProps) {
  return (
    <div className={`space-y-5 ${className}`.trim()} data-testid={testId}>
      {children}
    </div>
  );
}
