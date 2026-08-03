"use client";

import { useState } from "react";
import {
  AGENCY_NEXT_STEPS,
  type AgencyNextStepId,
} from "@/lib/home/agency-analysis-flow";
import { useLocale } from "@/lib/i18n";

type Props = {
  selected: AgencyNextStepId[];
  onChange: (next: AgencyNextStepId[]) => void;
  onContinue: () => void;
  busy?: boolean;
};

export function AgencyNextSteps({ selected, onChange, onContinue, busy }: Props) {
  const { t } = useLocale();
  const [hintVisible, setHintVisible] = useState(false);
  const canContinue = !busy && selected.length > 0;

  const continueLabelKey = selected.includes("prepare_content")
    ? "agency.continuePrepareContent"
    : "agency.continueSelected";

  function toggle(id: AgencyNextStepId) {
    setHintVisible(false);
    if (selected.includes(id)) onChange(selected.filter((x) => x !== id));
    else onChange([...selected, id]);
  }

  function handleContinueClick() {
    if (canContinue) {
      onContinue();
      return;
    }
    setHintVisible(true);
  }

  return (
    <section
      className="space-y-4 rounded-xl border p-4 transition-shadow"
      style={{
        borderColor: hintVisible
          ? "color-mix(in srgb, var(--ms-brand-primary) 55%, var(--ms-border-default))"
          : "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
        boxShadow: hintVisible
          ? "0 0 0 2px color-mix(in srgb, var(--ms-brand-primary) 25%, transparent)"
          : undefined,
      }}
      data-testid="agency-next-steps"
      data-hint-visible={hintVisible ? "true" : "false"}
    >
      <h3 className="text-lg font-semibold" style={{ color: "var(--ms-text-primary)" }}>
        {t("agency.nextTitle")}
      </h3>
      <ul className="space-y-2">
        {AGENCY_NEXT_STEPS.map((step) => (
          <li key={step.id}>
            <label className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={selected.includes(step.id)}
                onChange={() => toggle(step.id)}
                data-testid={`agency-next-${step.id}`}
              />
              <span style={{ color: "var(--ms-text-primary)" }}>{t(step.labelKey)}</span>
            </label>
          </li>
        ))}
      </ul>
      {hintVisible && !canContinue ? (
        <p
          className="text-sm"
          style={{ color: "var(--ms-danger, #b42318)" }}
          data-testid="agency-next-continue-hint"
          role="status"
        >
          {t("agency.continueSelectedHint")}
        </p>
      ) : null}
      <button
        type="button"
        disabled={busy}
        aria-disabled={!canContinue}
        title={!canContinue ? t("agency.continueSelectedHint") : undefined}
        className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
        style={{
          background: "var(--ms-brand-primary)",
          color: "var(--ms-text-on-brand, #fff)",
          opacity: canContinue ? 1 : 0.55,
        }}
        data-testid="agency-next-continue"
        onClick={handleContinueClick}
      >
        {t(continueLabelKey)}
      </button>
    </section>
  );
}
