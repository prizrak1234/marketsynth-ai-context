type CommercialLoadingStateProps = {
  label?: string;
  variant?: "inline" | "card" | "list";
  lines?: number;
  testId?: string;
};

function PulseBar({ widthClass }: { widthClass: string }) {
  return (
    <div
      className={`h-3 animate-pulse rounded ${widthClass}`}
      style={{ background: "var(--ms-border-subtle)" }}
    />
  );
}

/** Canonical loading state for commercial surfaces (DESIGN.md §6). */
export function CommercialLoadingState({
  label,
  variant = "inline",
  lines = 3,
  testId = "commercial-loading-state",
}: CommercialLoadingStateProps) {
  if (variant === "inline") {
    return (
      <p
        className="text-sm"
        style={{ color: "var(--ms-text-muted)" }}
        data-testid={testId}
        role="status"
      >
        {label ?? "…"}
      </p>
    );
  }

  if (variant === "list") {
    return (
      <ul className="space-y-2" data-testid={testId} role="status" aria-label={label}>
        {Array.from({ length: lines }).map((_, index) => (
          <li
            key={index}
            className="rounded-lg border px-4 py-3"
            style={{ borderColor: "var(--ms-border-default)" }}
          >
            <PulseBar widthClass="w-1/3" />
            <div className="mt-2">
              <PulseBar widthClass="w-full" />
            </div>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div
      className="animate-pulse space-y-3 rounded-xl border p-4"
      style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
      data-testid={testId}
      role="status"
      aria-label={label}
    >
      <PulseBar widthClass="w-1/3" />
      {Array.from({ length: lines }).map((_, index) => (
        <PulseBar key={index} widthClass={index === lines - 1 ? "w-4/5" : "w-full"} />
      ))}
    </div>
  );
}
