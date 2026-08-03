"use client";

import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { fetchBusinessCampaignSupervisorReport } from "@/lib/api/endpoints/business-campaigns";
import type {
  CampaignAction,
  CampaignActionType,
  CampaignSupervisorFinding,
} from "@/lib/api/types/business-campaigns";

type CampaignSupervisorPanelProps = {
  projectId: string;
  campaignId: string;
  healthScore: number;
  findingsCount: number;
  criticalCount: number;
  topFindings: CampaignSupervisorFinding[];
  availableActions?: CampaignAction[];
  onRunAction?: (action: CampaignAction) => void;
};

function severityClass(severity: CampaignSupervisorFinding["severity"]) {
  if (severity === "critical") return "text-destructive";
  if (severity === "warning") return "text-amber-600 dark:text-amber-400";
  return "text-muted-foreground";
}

function actionForFinding(
  finding: CampaignSupervisorFinding,
  availableActions: CampaignAction[] | undefined,
): CampaignAction | undefined {
  if (!finding.recommended_action_type || !availableActions?.length) return undefined;
  return availableActions.find(
    (action) => action.type === finding.recommended_action_type && action.enabled,
  );
}

export function CampaignSupervisorPanel({
  projectId,
  campaignId,
  healthScore,
  findingsCount,
  criticalCount,
  topFindings,
  availableActions = [],
  onRunAction,
}: CampaignSupervisorPanelProps) {
  const reportQuery = useQuery({
    queryKey: ["campaign-supervisor-report", projectId, campaignId],
    queryFn: () => fetchBusinessCampaignSupervisorReport(projectId, campaignId),
    enabled: Boolean(projectId && campaignId),
  });

  const report = reportQuery.data;
  const missingInputs = report?.missing_inputs ?? [];
  const contradictions = report?.contradictions ?? [];
  const risks = report?.risks ?? [];

  if (findingsCount === 0 && healthScore >= 95) {
    return (
      <div className="rounded-md border border-border bg-muted/20 p-2 text-[10px] text-muted-foreground">
        Campaign quality looks healthy ({healthScore}/100). No supervisor warnings.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-muted/20 p-2">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Campaign quality
        </p>
        <span className="rounded bg-background px-1.5 py-0.5 text-[10px] font-medium">
          {healthScore}/100
        </span>
      </div>
      <p className="mb-2 text-[10px] text-muted-foreground">
        Read-only supervisor — gaps and risks only, no auto-fix.
        {criticalCount ? ` · ${criticalCount} critical` : ""}
        {findingsCount ? ` · ${findingsCount} findings` : ""}
      </p>

      {topFindings.length ? (
        <div className="space-y-2">
          {topFindings.map((finding) => {
            const action = actionForFinding(finding, availableActions);
            return (
              <div
                key={`${finding.category}-${finding.title}`}
                className="rounded border border-border/60 bg-background/40 p-2 text-[10px]"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className={`font-medium ${severityClass(finding.severity)}`}>
                      {finding.title}
                    </p>
                    <p className="mt-0.5 text-muted-foreground">{finding.description}</p>
                  </div>
                  {action && onRunAction ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 shrink-0 text-[10px]"
                      onClick={() => onRunAction(action)}
                    >
                      {action.label}
                    </Button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {missingInputs.length ? (
        <div className="mt-2">
          <p className="mb-1 text-[10px] font-semibold text-muted-foreground">Missing inputs</p>
          <ul className="list-disc pl-4 text-[10px] text-muted-foreground">
            {missingInputs.map((item) => (
              <li key={item}>{item.replace(/_/g, " ")}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {contradictions.length ? (
        <div className="mt-2">
          <p className="mb-1 text-[10px] font-semibold text-amber-600 dark:text-amber-400">
            Contradictions
          </p>
          <ul className="list-disc pl-4 text-[10px] text-muted-foreground">
            {contradictions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {risks.length ? (
        <div className="mt-2">
          <p className="mb-1 text-[10px] font-semibold text-destructive">Risks</p>
          <ul className="list-disc pl-4 text-[10px] text-muted-foreground">
            {risks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {report?.recommended_next_actions?.length ? (
        <p className="mt-2 text-[9px] text-muted-foreground">
          Suggested fixes map to Action Center buttons — run them explicitly when ready.
        </p>
      ) : null}
    </div>
  );
}
