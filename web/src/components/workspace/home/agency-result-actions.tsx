"use client";

import { useLocale } from "@/lib/i18n";

type Props = {
  onContinueWork: () => void;
  onDownloadReport: () => void;
  onNewProject: () => void;
  onStartResearch?: () => void;
  onRefineInputs?: () => void;
  onRetryResearch?: () => void;
  showContinue?: boolean;
  showStartResearch?: boolean;
  showRefineInputs?: boolean;
  showRetryResearch?: boolean;
  showDownloadReport?: boolean;
  busy?: boolean;
};

export function AgencyResultActions({
  onContinueWork,
  onDownloadReport,
  onNewProject,
  onStartResearch,
  onRefineInputs,
  onRetryResearch,
  showContinue = true,
  showStartResearch = false,
  showRefineInputs = false,
  showRetryResearch = false,
  showDownloadReport = true,
  busy,
}: Props) {
  const { t } = useLocale();
  return (
    <div className="flex flex-wrap gap-2" data-testid="agency-result-actions">
      {showRefineInputs && onRefineInputs ? (
        <button
          type="button"
          disabled={busy}
          className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-on-brand, #fff)",
          }}
          data-testid="agency-action-refine-inputs"
          onClick={onRefineInputs}
        >
          {t("agency.action.refineInputs")}
        </button>
      ) : null}
      {showRetryResearch && onRetryResearch ? (
        <button
          type="button"
          disabled={busy}
          className="rounded-md border px-4 py-2 text-sm font-semibold disabled:opacity-50"
          style={{
            borderColor: "var(--ms-border-default)",
            color: "var(--ms-text-primary)",
          }}
          data-testid="agency-action-retry-research"
          onClick={onRetryResearch}
        >
          {t("agency.action.retryResearch")}
        </button>
      ) : null}
      {showStartResearch && onStartResearch ? (
        <button
          type="button"
          disabled={busy}
          className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
          style={{
            background: "var(--ms-brand-primary)",
            color: "var(--ms-text-on-brand, #fff)",
          }}
          data-testid="agency-action-start-research"
          onClick={onStartResearch}
        >
          {t("agency.action.startResearch")}
        </button>
      ) : null}
      {showContinue ? (
        <button
          type="button"
          disabled={busy}
          className="rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
          style={
            showStartResearch || showRefineInputs
              ? {
                  border: "1px solid var(--ms-border-default)",
                  color: "var(--ms-text-primary)",
                }
              : {
                  background: "var(--ms-brand-primary)",
                  color: "var(--ms-text-on-brand, #fff)",
                }
          }
          data-testid="agency-action-continue"
          onClick={onContinueWork}
        >
          {t("agency.action.continue")}
        </button>
      ) : null}
      {showDownloadReport ? (
      <button
        type="button"
        className="rounded-md border px-4 py-2 text-sm font-semibold"
        style={{
          borderColor: "var(--ms-border-default)",
          color: "var(--ms-text-primary)",
        }}
        data-testid="agency-action-download"
        onClick={onDownloadReport}
      >
        {t("agency.action.download")}
      </button>
      ) : null}
      <button
        type="button"
        className="rounded-md border px-4 py-2 text-sm font-semibold"
        style={{
          borderColor: "var(--ms-border-default)",
          color: "var(--ms-text-primary)",
        }}
        data-testid="agency-action-new"
        onClick={onNewProject}
      >
        {t("agency.action.newProject")}
      </button>
    </div>
  );
}
