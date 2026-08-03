import type { ReactNode } from "react";

type CommercialAlertTone = "info" | "warning" | "danger" | "success";

type CommercialAlertProps = {
  tone?: CommercialAlertTone;
  title: string;
  message?: string;
  hint?: string;
  hintLabel?: string;
  actions?: ReactNode;
  testId?: string;
};

const toneBorder: Record<CommercialAlertTone, string> = {
  info: "var(--ms-status-info)",
  warning: "var(--ms-status-warning)",
  danger: "var(--ms-danger, var(--ms-status-danger))",
  success: "var(--ms-status-success)",
};

const toneTitle: Record<CommercialAlertTone, string> = {
  info: "var(--ms-status-info)",
  warning: "var(--ms-status-warning)",
  danger: "var(--ms-danger, var(--ms-status-danger))",
  success: "var(--ms-status-success)",
};

/** Alert / failure / notice surface (DESIGN.md §7.4, §9). */
export function CommercialAlert({
  tone = "danger",
  title,
  message,
  hint,
  hintLabel,
  actions,
  testId,
}: CommercialAlertProps) {
  return (
    <div
      role="alert"
      className="space-y-4 rounded-xl border p-4"
      style={{
        borderColor: toneBorder[tone],
        background: "var(--ms-bg-surface)",
      }}
      data-testid={testId}
    >
      <div className="space-y-1">
        <p className="text-sm font-semibold" style={{ color: toneTitle[tone] }}>
          {title}
        </p>
        {message ? (
          <p className="text-sm" style={{ color: "var(--ms-text-primary)" }}>
            {message}
          </p>
        ) : null}
      </div>
      {hint ? (
        <div className="space-y-1">
          {hintLabel ? (
            <p
              className="text-xs font-medium uppercase tracking-wide"
              style={{ color: "var(--ms-text-muted)" }}
            >
              {hintLabel}
            </p>
          ) : null}
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {hint}
          </p>
        </div>
      ) : null}
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
