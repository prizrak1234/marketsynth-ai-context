"use client";

import type { CommercialErrorView } from "@/lib/errors/commercial-error-mapper";
import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { CommercialButton } from "@/components/commercial/commercial-button";

type ResearchFailurePanelProps = {
  failure: CommercialErrorView;
  busy?: boolean;
  showBackToReport?: boolean;
  onRetry: () => void;
  onBackToReport?: () => void;
  labels: {
    reasonLabel: string;
    retry: string;
    backToReport: string;
    reportIssue: string;
  };
};

export function ResearchFailurePanel({
  failure,
  busy = false,
  showBackToReport = false,
  onRetry,
  onBackToReport,
  labels,
}: ResearchFailurePanelProps) {
  return (
    <CommercialAlert
      tone="danger"
      title={failure.title}
      message={failure.message}
      hint={failure.actionHint}
      hintLabel={labels.reasonLabel}
      testId="biv-research-failed"
      actions={
        <>
          <CommercialButton
            variant="primary"
            disabled={busy}
            onClick={onRetry}
            testId="biv-research-failed-retry"
          >
            {labels.retry}
          </CommercialButton>
          {showBackToReport && onBackToReport ? (
            <CommercialButton
              variant="secondary"
              disabled={busy}
              onClick={onBackToReport}
              testId="biv-research-failed-back"
            >
              {labels.backToReport}
            </CommercialButton>
          ) : null}
        </>
      }
    />
  );
}
