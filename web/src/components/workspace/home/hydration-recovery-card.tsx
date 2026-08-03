"use client";

import type { AnalysisContextRecord } from "@/lib/api/endpoints/analysis-contexts";
import { useLocale } from "@/lib/i18n";

type Props = {
  context: AnalysisContextRecord;
  busy?: boolean;
  onContinue: () => void;
  onEdit: () => void;
  onStartNew: () => void;
};

function dataSourceLabel(
  label: AnalysisContextRecord["data_source_label"],
  t: (key: string) => string,
): string {
  switch (label) {
    case "saved_project":
      return t("biv.recovery.sourceSavedProject");
    case "previous_session":
      return t("biv.recovery.sourcePreviousSession");
    case "restored_draft":
      return t("biv.recovery.sourceRestoredDraft");
    default:
      return t("biv.recovery.sourceSavedProject");
  }
}

export function HydrationRecoveryCard({
  context,
  busy = false,
  onContinue,
  onEdit,
  onStartNew,
}: Props) {
  const { t } = useLocale();
  const updated = new Date(context.updated_at).toLocaleString("ru-RU");

  return (
    <div
      className="space-y-4 rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-brand-secondary, #6366f1)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="hydration-recovery-card"
    >
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">{t("biv.recovery.title")}</h2>
        <p className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
          {dataSourceLabel(context.data_source_label, t)} · {updated}
        </p>
      </div>

      <div className="space-y-2 text-sm">
        <p>
          <span className="font-medium">{t("biv.intake.field.idea")}: </span>
          {context.idea_description || t("biv.recovery.noIdea")}
        </p>
        {context.target_customer ? (
          <p>
            <span className="font-medium">{t("biv.intake.field.audience")}: </span>
            {context.target_customer}
          </p>
        ) : null}
        {context.geography ? (
          <p>
            <span className="font-medium">{t("biv.intake.field.geography")}: </span>
            {context.geography}
          </p>
        ) : null}
        {context.business_model ? (
          <p>
            <span className="font-medium">{t("biv.intake.field.businessModel")}: </span>
            {context.business_model}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: "var(--ms-brand-primary)" }}
          disabled={busy}
          onClick={onContinue}
          data-testid="recovery-continue-button"
        >
          {t("biv.recovery.continue")}
        </button>
        <button
          type="button"
          className="rounded-lg border px-4 py-2 text-sm font-semibold disabled:opacity-50"
          disabled={busy}
          onClick={onEdit}
          data-testid="recovery-edit-button"
        >
          {t("biv.recovery.edit")}
        </button>
        <button
          type="button"
          className="rounded-lg border px-4 py-2 text-sm font-semibold disabled:opacity-50"
          disabled={busy}
          onClick={onStartNew}
          data-testid="recovery-start-new-button"
        >
          {t("biv.recovery.startNew")}
        </button>
      </div>
    </div>
  );
}
