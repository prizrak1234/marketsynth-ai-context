import type { ReactNode } from "react";

type CommercialBadgeTone = "neutral" | "info" | "warning" | "success" | "danger";

type CommercialBadgeProps = {
  children: ReactNode;
  tone?: CommercialBadgeTone;
  uppercase?: boolean;
};

const toneColor: Record<CommercialBadgeTone, string> = {
  neutral: "var(--ms-text-muted)",
  info: "var(--ms-status-info)",
  warning: "var(--ms-status-warning)",
  success: "var(--ms-status-success)",
  danger: "var(--ms-status-danger)",
};

/** Status / lifecycle chip for commercial surfaces (DESIGN.md §5). */
export function CommercialBadge({
  children,
  tone = "neutral",
  uppercase = false,
}: CommercialBadgeProps) {
  return (
    <span
      className={`text-xs font-medium ${uppercase ? "uppercase tracking-wide" : ""}`}
      style={{ color: toneColor[tone] }}
    >
      {children}
    </span>
  );
}
