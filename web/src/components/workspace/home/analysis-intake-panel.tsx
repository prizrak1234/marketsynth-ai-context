"use client";

import { useEffect, useRef } from "react";
import type { AnalysisContextFields, AnalysisContextRecord } from "@/lib/api/endpoints/analysis-contexts";
import {
  BLOCKING_FIELD_KEYS,
  OPTIONAL_RESEARCH_GAP_FIELDS,
} from "@/lib/biv/analysis-context-specificity";
import {
  INTAKE_FIELD_HTML_ATTRS,
  type IntakeFieldKey,
} from "@/lib/biv/intake-field-attributes";
import { useLocale } from "@/lib/i18n";

const FIELD_LABELS: Record<string, string> = {
  idea_description: "biv.intake.field.idea",
  product_or_service: "biv.intake.field.product",
  target_customer: "biv.intake.field.audience",
  geography: "biv.intake.field.geography",
  analysis_goal: "biv.intake.field.goal",
  pricing_or_revenue_model: "biv.intake.field.pricing",
  known_competitors: "biv.intake.field.competitors",
  current_stage: "biv.intake.field.stage",
  budget_context: "biv.intake.field.budget",
};

const FIELD_TEST_IDS: Record<string, string> = {
  idea_description: "intake-idea-description",
  product_or_service: "intake-product",
  target_customer: "intake-audience",
  geography: "intake-geography",
  analysis_goal: "intake-goal",
  pricing_or_revenue_model: "intake-pricing",
  known_competitors: "intake-competitors",
  current_stage: "intake-stage",
  budget_context: "intake-budget",
};

type Props = {
  context: AnalysisContextRecord;
  busy?: boolean;
  error?: string | null;
  focusFieldsOnMount?: string[];
  onChange: (fields: AnalysisContextFields) => void;
  onConfirm: () => void;
};

function isFieldUnknown(value: string | null | undefined): boolean {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized === "неизвестно" || normalized === "unknown";
}

export function AnalysisIntakePanel({
  context,
  busy = false,
  error = null,
  focusFieldsOnMount = [],
  onChange,
  onConfirm,
}: Props) {
  const { t } = useLocale();
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({});

  function focusField(field: string) {
    const node = fieldRefs.current[field];
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "center" });
    const focusable = node.querySelector<HTMLElement>(
      "textarea, input:not([type='checkbox'])",
    );
    focusable?.focus();
  }

  useEffect(() => {
    if (focusFieldsOnMount.length === 0) return;
    const first = focusFieldsOnMount.find((field) => fieldRefs.current[field]);
    if (first) focusField(first);
  }, [focusFieldsOnMount]);

  function update(partial: AnalysisContextFields) {
    onChange({
      idea_description: context.idea_description,
      product_or_service: context.product_or_service,
      target_customer: context.target_customer,
      geography: context.geography,
      business_model: context.business_model,
      pricing_or_revenue_model: context.pricing_or_revenue_model,
      current_stage: context.current_stage,
      budget_context: context.budget_context,
      known_competitors: context.known_competitors,
      analysis_goal: context.analysis_goal,
      target_customer_unknown: context.target_customer_unknown,
      geography_unknown: context.geography_unknown,
      ...partial,
    });
  }

  const researchGapWarnings = context.warnings.filter((w) => w.startsWith("research_gap_"));
  const canConfirm = context.missing_fields.length === 0;

  return (
    <form
      className="space-y-4 rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-border-subtle)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="analysis-intake-panel"
      autoComplete="off"
      onSubmit={(e) => {
        e.preventDefault();
        if (canConfirm && !busy) onConfirm();
      }}
    >
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">{t("biv.intake.whatToValidate")}</h2>
        <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {t("biv.intake.confirmBeforeRun")}
        </p>
      </div>

      <label
        className="block space-y-1 text-sm"
        ref={(el) => {
          fieldRefs.current.idea_description = el;
        }}
      >
        <span>{t("biv.intake.field.idea")} *</span>
        <textarea
          className="w-full rounded-lg border px-3 py-2 text-sm"
          style={{
            borderColor: "var(--ms-border-subtle)",
            background: "var(--ms-bg-canvas)",
            color: "var(--ms-text-primary)",
          }}
          rows={3}
          value={context.idea_description}
          onChange={(e) => update({ idea_description: e.target.value })}
          data-testid="intake-idea-description"
          id={INTAKE_FIELD_HTML_ATTRS.idea_description.id}
          name={INTAKE_FIELD_HTML_ATTRS.idea_description.name}
          autoComplete={INTAKE_FIELD_HTML_ATTRS.idea_description.autoComplete}
        />
      </label>

      <label
        className="block space-y-1 text-sm"
        ref={(el) => {
          fieldRefs.current.product_or_service = el;
        }}
      >
        <span>{t("biv.intake.field.product")} *</span>
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          style={{
            borderColor: "var(--ms-border-subtle)",
            background: "var(--ms-bg-canvas)",
            color: "var(--ms-text-primary)",
          }}
          value={context.product_or_service ?? ""}
          onChange={(e) => update({ product_or_service: e.target.value })}
          data-testid="intake-product"
          id={INTAKE_FIELD_HTML_ATTRS.product_or_service.id}
          name={INTAKE_FIELD_HTML_ATTRS.product_or_service.name}
          autoComplete={INTAKE_FIELD_HTML_ATTRS.product_or_service.autoComplete}
          type="text"
        />
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label
          className="block space-y-1 text-sm"
          ref={(el) => {
            fieldRefs.current.target_customer = el;
          }}
        >
          <span>{t("biv.intake.field.audience")} *</span>
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-subtle)",
              background: "var(--ms-bg-canvas)",
              color: "var(--ms-text-primary)",
            }}
            value={context.target_customer ?? ""}
            disabled={context.target_customer_unknown}
            onChange={(e) => update({ target_customer: e.target.value })}
            data-testid="intake-audience"
            id={INTAKE_FIELD_HTML_ATTRS.target_customer.id}
            name={INTAKE_FIELD_HTML_ATTRS.target_customer.name}
            autoComplete={INTAKE_FIELD_HTML_ATTRS.target_customer.autoComplete}
            type="text"
          />
          <label className="flex items-center gap-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            <input
              type="checkbox"
              checked={context.target_customer_unknown}
              data-testid="intake-audience-unknown"
              onChange={(e) =>
                update({
                  target_customer_unknown: e.target.checked,
                  target_customer: e.target.checked ? "неизвестно" : context.target_customer,
                })
              }
            />
            {t("biv.intake.unknownAudience")}
          </label>
        </label>

        <label
          className="block space-y-1 text-sm"
          ref={(el) => {
            fieldRefs.current.geography = el;
          }}
        >
          <span>{t("biv.intake.field.geography")} *</span>
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-subtle)",
              background: "var(--ms-bg-canvas)",
              color: "var(--ms-text-primary)",
            }}
            value={context.geography ?? ""}
            disabled={context.geography_unknown}
            onChange={(e) => update({ geography: e.target.value })}
            data-testid="intake-geography"
            id={INTAKE_FIELD_HTML_ATTRS.geography.id}
            name={INTAKE_FIELD_HTML_ATTRS.geography.name}
            autoComplete={INTAKE_FIELD_HTML_ATTRS.geography.autoComplete}
            type="text"
          />
          <label className="flex items-center gap-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            <input
              type="checkbox"
              checked={context.geography_unknown}
              data-testid="intake-geography-unknown"
              onChange={(e) =>
                update({
                  geography_unknown: e.target.checked,
                  geography: e.target.checked ? "неизвестно" : context.geography,
                })
              }
            />
            {t("biv.intake.unknownGeography")}
          </label>
        </label>
      </div>

      <label
        className="block space-y-1 text-sm"
        ref={(el) => {
          fieldRefs.current.analysis_goal = el;
        }}
      >
        <span>{t("biv.intake.field.goal")} *</span>
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          style={{
            borderColor: "var(--ms-border-subtle)",
            background: "var(--ms-bg-canvas)",
            color: "var(--ms-text-primary)",
          }}
          value={context.analysis_goal ?? ""}
          onChange={(e) => update({ analysis_goal: e.target.value })}
          data-testid="intake-goal"
          id={INTAKE_FIELD_HTML_ATTRS.analysis_goal.id}
          name={INTAKE_FIELD_HTML_ATTRS.analysis_goal.name}
          autoComplete={INTAKE_FIELD_HTML_ATTRS.analysis_goal.autoComplete}
          type="text"
        />
      </label>

      <div
        className="space-y-3 rounded-lg border p-4"
        style={{ borderColor: "var(--ms-border-subtle)" }}
        data-testid="intake-optional-fields"
      >
        <div>
          <p className="text-sm font-medium">{t("biv.intake.optionalSectionTitle")}</p>
          <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {t("biv.intake.optionalSectionHint")}
          </p>
        </div>

        {OPTIONAL_RESEARCH_GAP_FIELDS.map((fieldKey) => {
          const value = context[fieldKey as keyof AnalysisContextRecord];
          const strValue = typeof value === "string" ? value : "";
          const unknown = isFieldUnknown(strValue);
          const htmlAttrs = INTAKE_FIELD_HTML_ATTRS[fieldKey as IntakeFieldKey];
          return (
            <label
              key={fieldKey}
              className="block space-y-1 text-sm"
              ref={(el) => {
                fieldRefs.current[fieldKey] = el;
              }}
            >
              <span>{t(FIELD_LABELS[fieldKey] ?? fieldKey)}</span>
              <input
                className="w-full rounded-lg border px-3 py-2 text-sm"
                style={{
                  borderColor: "var(--ms-border-subtle)",
                  background: "var(--ms-bg-canvas)",
                  color: "var(--ms-text-primary)",
                }}
                value={unknown ? "" : strValue}
                disabled={unknown}
                placeholder={unknown ? t("biv.intake.unknownOptional") : undefined}
                onChange={(e) =>
                  update({ [fieldKey]: e.target.value } as AnalysisContextFields)
                }
                data-testid={FIELD_TEST_IDS[fieldKey]}
                id={htmlAttrs.id}
                name={htmlAttrs.name}
                autoComplete={htmlAttrs.autoComplete}
                type={htmlAttrs.type ?? "text"}
                inputMode={htmlAttrs.inputMode}
                data-1p-ignore="true"
                data-lpignore="true"
              />
              <label
                className="flex items-center gap-2 text-xs"
                style={{ color: "var(--ms-text-secondary)" }}
              >
                <input
                  type="checkbox"
                  checked={unknown}
                  onChange={(e) =>
                    update({
                      [fieldKey]: e.target.checked ? "неизвестно" : "",
                    } as AnalysisContextFields)
                  }
                />
                {t("biv.intake.unknownOptional")}
              </label>
            </label>
          );
        })}
      </div>

      {context.missing_fields.length > 0 ? (
        <div
          className="rounded-lg border px-3 py-2 text-sm"
          style={{
            background: "var(--ms-warning-bg, color-mix(in srgb, var(--ms-brand-warning, #eab308) 18%, var(--ms-bg-surface)))",
            borderColor: "var(--ms-warning-border, color-mix(in srgb, var(--ms-brand-warning, #eab308) 45%, var(--ms-border-subtle)))",
            color: "var(--ms-text-primary)",
          }}
          data-testid="intake-missing-fields"
          role="alert"
        >
          <p className="font-medium">{t("biv.intake.missingData")}</p>
          <p className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {t("biv.intake.missingDataHint")}
          </p>
          <ul className="mt-2 space-y-1">
            {context.missing_fields.map((field) => (
              <li key={field}>
                <button
                  type="button"
                  className="text-left underline underline-offset-2"
                  style={{ color: "var(--ms-text-primary)" }}
                  onClick={() => focusField(field)}
                  data-testid={`intake-missing-link-${field}`}
                >
                  {t(FIELD_LABELS[field] ?? field)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {researchGapWarnings.length > 0 && context.missing_fields.length === 0 ? (
        <div
          className="rounded-lg border px-3 py-2 text-sm"
          style={{
            background: "var(--ms-bg-canvas)",
            borderColor: "var(--ms-border-subtle)",
            color: "var(--ms-text-secondary)",
          }}
          data-testid="intake-research-gaps"
        >
          {t("biv.intake.researchGapsNotice")}
        </div>
      ) : null}

      {error ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        style={{ background: "var(--ms-brand-primary)" }}
        disabled={busy || !canConfirm}
        title={!canConfirm ? t("biv.intake.confirmDisabledHint") : undefined}
        data-testid="intake-confirm-button"
        aria-disabled={busy || !canConfirm}
      >
        {t("biv.intake.confirmAndContinue")}
      </button>

      {!canConfirm ? (
        <p className="text-xs" style={{ color: "var(--ms-text-secondary)" }} data-testid="intake-required-hint">
          {t("biv.intake.requiredFieldsHint", {
            fields: BLOCKING_FIELD_KEYS.map((f) => t(FIELD_LABELS[f])).join(", "),
          })}
        </p>
      ) : null}
    </form>
  );
}
