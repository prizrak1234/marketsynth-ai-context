import type { ReactNode } from "react";

type CommercialStatusTone = "neutral" | "info" | "warning" | "success" | "danger";

type CommercialStatusProps = {
  children: ReactNode;
  tone?: CommercialStatusTone;
  testId?: string;
};

const toneStyles: Record<
  CommercialStatusTone,
  { color: string; background: string; border: string }
> = {
  neutral: {
    color: "var(--ms-text-muted)",
    background: "var(--ms-bg-elevated)",
    border: "var(--ms-border-default)",
  },
  info: {
    color: "var(--ms-status-info)",
    background: "var(--ms-bg-elevated)",
    border: "var(--ms-border-default)",
  },
  warning: {
    color: "var(--ms-status-warning)",
    background: "var(--ms-bg-elevated)",
    border: "var(--ms-border-default)",
  },
  success: {
    color: "var(--ms-status-success)",
    background: "var(--ms-bg-elevated)",
    border: "var(--ms-border-default)",
  },
  danger: {
    color: "var(--ms-status-danger)",
    background: "var(--ms-bg-elevated)",
    border: "var(--ms-border-default)",
  },
};

/** Lifecycle / status chip on cards and lists (DESIGN.md §6). */
export function CommercialStatus({
  children,
  tone = "neutral",
  testId,
}: CommercialStatusProps) {
  const styles = toneStyles[tone];
  return (
    <span
      className="inline-flex shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium"
      style={{
        color: styles.color,
        background: styles.background,
        borderColor: styles.border,
      }}
      data-testid={testId}
    >
      {children}
    </span>
  );
}
