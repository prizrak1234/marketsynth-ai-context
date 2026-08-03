type CommercialProgressProps = {
  label: string;
  value: number;
  testId?: string;
};

/** Confidence / coverage bar (DESIGN.md domain tokens). */
export function CommercialProgress({ label, value, testId }: CommercialProgressProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="space-y-1" data-testid={testId}>
      <div className="flex justify-between text-sm">
        <span id={`${testId ?? "progress"}-label`}>{label}</span>
        <span className="font-medium">{clamped}%</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full"
        style={{ background: "var(--ms-bg-canvas)" }}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        aria-labelledby={`${testId ?? "progress"}-label`}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${clamped}%`,
            background: "var(--ms-accent, var(--ms-brand-primary))",
          }}
        />
      </div>
    </div>
  );
}
