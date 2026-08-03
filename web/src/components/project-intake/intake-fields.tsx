"use client";

import type { CSSProperties, ReactNode } from "react";

import { IntakeStepFrame } from "@/components/commercial/form/intake-step-frame";
import { useIntakeWizardCopy } from "@/lib/project-intake/use-intake-wizard-copy";
import { cn } from "@/lib/utils";

export function FieldLabel({
  htmlFor,
  children,
  required,
}: {
  htmlFor: string;
  children: ReactNode;
  required?: boolean;
}) {
  const copy = useIntakeWizardCopy();
  return (
    <label
      htmlFor={htmlFor}
      className="mb-1.5 block text-sm font-medium"
      style={{ color: "var(--ms-text-primary)" }}
    >
      {children}
      {required ? (
        <span
          className="ml-2 text-xs font-normal"
          style={{ color: "var(--ms-text-muted)" }}
        >
          · {copy.field.requiredMarker}
        </span>
      ) : (
        <span className="ml-2 text-xs font-normal" style={{ color: "var(--ms-text-muted)" }}>
          · {copy.field.optionalMarker}
        </span>
      )}
    </label>
  );
}

export function FieldHint({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="mt-1 text-xs leading-relaxed" style={{ color: "var(--ms-text-muted)" }}>
      {children}
    </p>
  );
}

export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-1 text-xs" style={{ color: "var(--ms-status-danger)" }} role="alert">
      {message}
    </p>
  );
}

const controlStyle: CSSProperties = {
  background: "var(--ms-bg-elevated)",
  color: "var(--ms-text-primary)",
  borderColor: "var(--ms-border-default)",
};

const focusRing =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ms-brand-primary)]";

export function TextInput({
  id,
  value,
  onChange,
  error,
  required,
  type = "text",
  placeholder,
  describedBy,
  disabled,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  required?: boolean;
  type?: string;
  placeholder?: string;
  describedBy?: string;
  disabled?: boolean;
}) {
  const errorId = `${id}-error`;
  return (
    <div>
      <input
        id={id}
        type={type}
        value={value}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={[describedBy, error ? errorId : null].filter(Boolean).join(" ") || undefined}
        onChange={(e) => onChange(e.target.value)}
        className={cn("w-full rounded-md border px-3 py-2 text-sm outline-none min-h-[44px]", focusRing)}
        style={{
          ...controlStyle,
          boxShadow: error ? "0 0 0 1px var(--ms-status-danger)" : undefined,
          opacity: disabled ? 0.6 : undefined,
        }}
      />
      <FieldError id={errorId} message={error} />
    </div>
  );
}

export function TextTextarea({
  id,
  value,
  onChange,
  error,
  required,
  rows = 4,
  placeholder,
  describedBy,
  disabled,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  required?: boolean;
  rows?: number;
  placeholder?: string;
  describedBy?: string;
  disabled?: boolean;
}) {
  const errorId = `${id}-error`;
  return (
    <div>
      <textarea
        id={id}
        value={value}
        rows={rows}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={[describedBy, error ? errorId : null].filter(Boolean).join(" ") || undefined}
        onChange={(e) => onChange(e.target.value)}
        className={cn("w-full rounded-md border px-3 py-2 text-sm outline-none", focusRing)}
        style={{
          ...controlStyle,
          boxShadow: error ? "0 0 0 1px var(--ms-status-danger)" : undefined,
          opacity: disabled ? 0.6 : undefined,
        }}
      />
      <FieldError id={errorId} message={error} />
    </div>
  );
}

export function TextSelect({
  id,
  value,
  onChange,
  options,
  error,
  required,
  placeholder = "Выберите…",
  describedBy,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  options: ReadonlyArray<{ value: string; label: string }>;
  error?: string;
  required?: boolean;
  placeholder?: string;
  describedBy?: string;
}) {
  const errorId = `${id}-error`;
  return (
    <div>
      <select
        id={id}
        value={value}
        required={required}
        aria-invalid={Boolean(error)}
        aria-describedby={[describedBy, error ? errorId : null].filter(Boolean).join(" ") || undefined}
        onChange={(e) => onChange(e.target.value)}
        className={cn("w-full rounded-md border px-3 py-2 text-sm outline-none min-h-[44px]", focusRing)}
        style={{
          ...controlStyle,
          boxShadow: error ? "0 0 0 1px var(--ms-status-danger)" : undefined,
        }}
      >
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <FieldError id={errorId} message={error} />
    </div>
  );
}

export function CheckboxRow({
  id,
  checked,
  onChange,
  children,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  children: ReactNode;
}) {
  return (
    <label
      htmlFor={id}
      className="flex min-h-[44px] cursor-pointer items-start gap-2 py-1 text-sm"
      style={{ color: "var(--ms-text-secondary)" }}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className={cn("mt-1", focusRing)}
      />
      <span>{children}</span>
    </label>
  );
}

export function MoneyField({
  id,
  label,
  required,
  value,
  onChange,
  unknownChecked,
  onUnknownChange,
  error,
  hint,
}: {
  id: string;
  label: string;
  required?: boolean;
  value: { mode: "exact" | "range" | "unknown"; exact?: string; min?: string; max?: string };
  onChange: (v: {
    mode: "exact" | "range" | "unknown";
    exact?: string;
    min?: string;
    max?: string;
  }) => void;
  unknownChecked?: boolean;
  onUnknownChange?: (v: boolean) => void;
  error?: string;
  hint?: string;
}) {
  const copy = useIntakeWizardCopy();
  const hintId = `${id}-hint`;
  return (
    <fieldset className="space-y-2">
      <legend className="mb-1.5 text-sm font-medium" style={{ color: "var(--ms-text-primary)" }}>
        {label}
        {required ? (
          <span className="ml-2 text-xs font-normal" style={{ color: "var(--ms-text-muted)" }}>
            · {copy.field.requiredMarker}
          </span>
        ) : (
          <span className="ml-2 text-xs font-normal" style={{ color: "var(--ms-text-muted)" }}>
            · {copy.field.optionalMarker}
          </span>
        )}
      </legend>
      {hint ? <FieldHint id={hintId}>{hint}</FieldHint> : null}
      <div className="flex flex-wrap gap-3 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        {(
          [
            ["exact", copy.money.modeExact],
            ["range", copy.money.modeRange],
            ["unknown", copy.money.modeUnknown],
          ] as const
        ).map(([mode, labelMode]) => (
          <label key={mode} className="inline-flex min-h-[44px] items-center gap-1.5">
            <input
              type="radio"
              name={`${id}-mode`}
              checked={value.mode === mode}
              className={focusRing}
              onChange={() =>
                onChange({
                  ...value,
                  mode,
                })
              }
            />
            {labelMode}
          </label>
        ))}
      </div>
      {value.mode === "exact" ? (
        <TextInput
          id={`${id}-exact`}
          value={value.exact ?? ""}
          onChange={(exact) => onChange({ ...value, mode: "exact", exact })}
          error={error}
          placeholder="500000"
          describedBy={hint ? hintId : undefined}
        />
      ) : null}
      {value.mode === "range" ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <TextInput
            id={`${id}-min`}
            value={value.min ?? ""}
            onChange={(min) => onChange({ ...value, mode: "range", min })}
            placeholder={copy.money.from}
            error={error}
          />
          <TextInput
            id={`${id}-max`}
            value={value.max ?? ""}
            onChange={(max) => onChange({ ...value, mode: "range", max })}
            placeholder={copy.money.to}
          />
        </div>
      ) : null}
      {value.mode === "unknown" ? (
        <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
          {copy.money.unknownValid}
        </p>
      ) : null}
      {onUnknownChange ? (
        <CheckboxRow
          id={`${id}-unknown-flag`}
          checked={Boolean(unknownChecked)}
          onChange={onUnknownChange}
        >
          {copy.money.markUnknown}
        </CheckboxRow>
      ) : null}
      {error && value.mode !== "exact" ? <FieldError id={`${id}-error`} message={error} /> : null}
    </fieldset>
  );
}

/** @deprecated Use IntakeStepFrame — kept for gradual migration. */
export function StepSection({
  title,
  description,
  children,
  "data-testid": dataTestId,
}: {
  title: string;
  description: string;
  children: ReactNode;
  "data-testid"?: string;
}) {
  return (
    <IntakeStepFrame title={title} description={description} testId={dataTestId}>
      {children}
    </IntakeStepFrame>
  );
}
