import type { ReactNode } from "react";

type CommercialCardProps = {
  children: ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg";
  testId?: string;
  /** Optional data attribute for research UI state tests. */
  researchUiState?: string;
};

const paddingClass = {
  sm: "p-3",
  md: "p-4 sm:p-5",
  lg: "px-5 py-8",
} as const;

/** Canonical bordered surface for commercial product UI (DESIGN.md §5). */
export function CommercialCard({
  children,
  className = "",
  padding = "md",
  testId,
  researchUiState,
}: CommercialCardProps) {
  return (
    <div
      className={`rounded-xl border ${paddingClass[padding]} ${className}`.trim()}
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid={testId}
      data-research-ui-state={researchUiState}
    >
      {children}
    </div>
  );
}

export function CommercialCardInset({
  children,
  className = "",
  testId,
}: Omit<CommercialCardProps, "padding">) {
  return (
    <div
      className={`rounded-lg border p-3 ${className}`.trim()}
      style={{ borderColor: "var(--ms-border-default)" }}
      data-testid={testId}
    >
      {children}
    </div>
  );
}
