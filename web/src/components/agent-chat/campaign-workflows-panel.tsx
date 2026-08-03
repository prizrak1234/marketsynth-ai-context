"use client";

import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { createCampaignWorkflowRun } from "@/lib/api/endpoints/business-campaigns";
import type {
  CampaignAction,
  CampaignWorkflowRunSummary,
  CampaignWorkflowStepView,
  CampaignWorkflowSuggestion,
} from "@/lib/api/types/business-campaigns";

type CampaignWorkflowsPanelProps = {
  projectId: string;
  campaignId: string;
  workflowSuggestions: CampaignWorkflowSuggestion[];
  activeWorkflow?: CampaignWorkflowRunSummary | null;
  availableActions?: CampaignAction[];
  onWorkflowCreated?: () => void;
  onRunAction?: (action: CampaignAction) => void;
};

function stepStatusLabel(status: CampaignWorkflowStepView["status"]) {
  if (status === "completed") return "Done";
  if (status === "current") return "Current";
  return "Pending";
}

function actionForStep(
  step: CampaignWorkflowStepView,
  availableActions: CampaignAction[] | undefined,
): CampaignAction | undefined {
  if (!step.recommended_action_type || !availableActions?.length) return undefined;
  return availableActions.find(
    (action) => action.type === step.recommended_action_type && action.enabled,
  );
}

export function CampaignWorkflowsPanel({
  projectId,
  campaignId,
  workflowSuggestions,
  activeWorkflow,
  availableActions = [],
  onWorkflowCreated,
  onRunAction,
}: CampaignWorkflowsPanelProps) {
  const createMutation = useMutation({
    mutationFn: (templateId: string) =>
      createCampaignWorkflowRun(projectId, campaignId, templateId),
    onSuccess: () => onWorkflowCreated?.(),
  });

  const createError =
    createMutation.error instanceof ApiError ? createMutation.error.message : null;

  if (!workflowSuggestions.length && !activeWorkflow) {
    return (
      <div className="rounded-md border border-border bg-muted/20 p-2 text-[10px] text-muted-foreground">
        No workflow templates recommended yet. Supervisor and brief signals will suggest
        repeatable processes here — nothing runs automatically.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-muted/20 p-2">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Campaign workflows
        </p>
        <span className="text-[9px] text-muted-foreground">Checklist only — no auto-run</span>
      </div>

      {workflowSuggestions.length ? (
        <div className="mb-3 space-y-2">
          <p className="text-[10px] font-semibold text-muted-foreground">Recommended</p>
          {workflowSuggestions.map((suggestion) => (
            <div
              key={suggestion.template_id}
              className="rounded border border-border/60 bg-background/40 p-2 text-[10px]"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-foreground">{suggestion.label}</p>
                  <p className="mt-0.5 text-muted-foreground">{suggestion.reason}</p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-7 shrink-0 text-[10px]"
                  disabled={createMutation.isPending}
                  onClick={() => createMutation.mutate(suggestion.template_id)}
                >
                  Start checklist
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {activeWorkflow ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-[10px] font-semibold text-foreground">
                {activeWorkflow.template_name}
              </p>
              <p className="text-[9px] text-muted-foreground">{activeWorkflow.template_goal}</p>
            </div>
            <span className="rounded bg-background px-1.5 py-0.5 text-[10px] font-medium">
              {activeWorkflow.progress_percent}%
            </span>
          </div>

          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${activeWorkflow.progress_percent}%` }}
            />
          </div>

          <ul className="space-y-1.5">
            {activeWorkflow.steps.map((step) => {
              const action = actionForStep(step, availableActions);
              return (
                <li
                  key={step.step_id}
                  className="flex flex-wrap items-start justify-between gap-2 rounded border border-border/40 bg-background/30 p-2 text-[10px]"
                >
                  <div>
                    <p className="font-medium text-foreground">
                      {step.step_index + 1}. {step.label}
                      <span className="ml-2 font-normal text-muted-foreground">
                        ({stepStatusLabel(step.status)})
                      </span>
                    </p>
                    <p className="mt-0.5 text-muted-foreground">{step.safe_description}</p>
                  </div>
                  {action && onRunAction && step.status !== "completed" ? (
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
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {createError ? (
        <p className="mt-2 text-[10px] text-destructive">{createError}</p>
      ) : null}
    </div>
  );
}
